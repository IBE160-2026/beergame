"""The Control test (Story 12.7, FR-82, AD-27, AD-12, AD-13): Admin-område → «Kontrolltest».

A Control test is an ordinary Class with one Class session of kind `control_test`, in the
operator's own Institution (`identity.operator_institution`), owned by the Admin who set it up.
`create` makes both in one transaction through `classes.service` and `sessions`' own repository,
pins the Scoring guide version under test (through the hook `tests.guide` registers) and the model
config under test (the session's `model_config_id`, referenced so it never changes; a trigger
keeps it), gives the session its own budget row and writes one audit row. The Admin then sets the
dates, the Roster, the Invitations and the allocation on the ordinary screens of Epics 4 and 5 as
the Class's owner (`authz.CONTROL_TEST_ACTIONS`). A Control test Class is in no staff list, takes
no other staff and no other Class session.

Only the routes of this module call it; it is `sessions`' own, beside `service.py`.
"""

import uuid
from datetime import datetime

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import budget, config
from app.modules.classes import service as classes
from app.modules.content import service as content
from app.modules.identity import service as identity
from app.modules.sessions import repo
from app.modules.sessions.schemas import (
    AiMode,
    ControlTestConfigOut,
    ControlTestGuideOut,
    ControlTestIn,
    ControlTestInstitutionOut,
    ControlTestOut,
    ControlTestsOut,
)
from app.modules.sessions.service import (
    CONTROL_TEST,
    DEFAULT_DEBRIEF_MODE,
    DEFAULT_INACTIVITY_LIMIT_HOURS,
    DEFAULT_OBLIGATORY,
    classic_settings,
    control_test_guide,
)
from app.platform import audit, authz, events
from app.platform.config import get_settings
from app.platform.db import get_sessionmaker

log = structlog.get_logger(__name__)

CONTROL_TEST_CREATED = "control_test.created"
"""The audit action of a Control test the Admin sets up (Story 12.7, AD-15)."""


class OperatorInstitutionMissing(Exception):
    """No Institution is marked as the operator's own (`operator_institution_missing`)."""


class InvalidControlTest(Exception):
    """The fields a new Control test is refused for: field → reason code, every one at once."""

    def __init__(self, fields: dict[str, str]) -> None:
        super().__init__(fields)
        self.fields = fields


def _guide_out(choice: content.ScoringGuideChoice) -> ControlTestGuideOut:
    return ControlTestGuideOut(
        id=choice.id,
        version=choice.version,
        edited=choice.edited,
        draft=choice.draft,
        created_at=choice.created_at,
    )


def _config_out(found: config.ModelConfig, default_id: uuid.UUID | None) -> ControlTestConfigOut:
    return ControlTestConfigOut(
        id=found.id,
        name=found.spec.name,
        model_version=found.spec.model_version,
        default=found.id == default_id,
    )


async def overview(user: authz.Principal) -> ControlTestsOut:
    """The Kontrolltest page for an Admin (`control_tests.manage`, checked by the route)."""
    default = await config.active_default()
    default_id = default.id if default else None
    configs = {found.id: found for found in await config.list_all()}
    operator = await identity.operator_institution()
    reader = control_test_guide().read
    async with get_sessionmaker().begin() as s:
        guides = await content.scoring_guide_choices(s)
        rows = await repo.control_test_rows(s)
        facts = await classes.class_facts(s, [row["class_id"] for row in rows])
        pinned = {row["id"]: await reader(s, row["id"]) for row in rows}
        owned = {
            row["class_id"]: user.id in await classes.owners_of(s, row["class_id"]) for row in rows
        }
    institutions = {
        found.id: found.name
        for found in await identity.list_institutions()
        if any(f.institution_id == found.id for f in facts.values())
    }
    items = []
    for row in rows:
        fact = facts.get(row["class_id"])
        if fact is None:  # pragma: no cover - a Class session never outlives its Class
            continue
        record = pinned[row["id"]]
        found = configs.get(row["model_config_id"]) if row["model_config_id"] else None
        items.append(
            ControlTestOut(
                id=row["id"],
                class_id=row["class_id"],
                name=fact.name,
                institution_name=institutions.get(fact.institution_id),
                created_at=row["created_at"],
                scoring_guide=ControlTestGuideOut(
                    id=record.id,
                    version=record.version,
                    edited=record.class_session_id is not None,
                    draft=record.guide.status == "draft",
                ),
                ai_config=_config_out(found, default_id) if found else None,
                can_open=owned[row["class_id"]],
            )
        )
    # The default config first, then the others oldest first, as `list_all` gives them.
    ordered = sorted(configs.values(), key=lambda c: c.id != default_id)
    return ControlTestsOut(
        operator_institution=(
            ControlTestInstitutionOut(id=operator.id, name=operator.name) if operator else None
        ),
        scoring_guides=[_guide_out(choice) for choice in guides],
        model_configs=[_config_out(found, default_id) for found in ordered],
        items=items,
    )


async def _checked_config(
    s: AsyncSession, config_id: uuid.UUID | None, refused: dict[str, str]
) -> config.ModelConfig | None:
    if config_id is None:
        refused["model_config_id"] = "missing"
        return None
    found = await config.get(config_id, session=s)
    if found is None:
        refused["model_config_id"] = "unknown"
    return found


async def create(user: authz.Principal, body: ControlTestIn, *, now: datetime) -> ControlTestOut:
    """Set up a Control test (Story 12.7, FR-82, AD-27): in one transaction a Class in the
    operator's own Institution with `user` as its owner and in it a Class session of kind
    `control_test`, pinned to `body`'s Scoring guide version and model config, with its own budget
    row, one audit row (ids and versions) and `user:<id>`. Raises `OperatorInstitutionMissing`
    when no Institution is marked, and `InvalidControlTest` with every refused field (`name`:
    the Class name rule's code; `scoring_guide_id`, `model_config_id`: `missing` or `unknown`);
    nothing is stored then. The route's policy (`control_tests.manage`) has checked the role."""
    session_id = uuid.uuid7()
    pin_guide = control_test_guide().pin
    async with get_sessionmaker().begin() as s:
        operator = await identity.operator_institution(s)
        if operator is None:
            log.info("control_test_refused", error_code="operator_institution_missing")
            raise OperatorInstitutionMissing
        refused: dict[str, str] = {}
        _, name_reason = classes.class_name(body.name)
        if name_reason:
            refused["name"] = name_reason
        found = await _checked_config(s, body.model_config_id, refused)
        if body.scoring_guide_id is None:
            refused["scoring_guide_id"] = "missing"
        elif body.scoring_guide_id not in {c.id for c in await content.scoring_guide_choices(s)}:
            refused["scoring_guide_id"] = "unknown"
        if refused or found is None or body.scoring_guide_id is None:
            log.info("control_test_refused", error_code="invalid_request", fields=sorted(refused))
            raise InvalidControlTest(refused)
        class_id = await classes.create_class_in(
            s, user.id, name=body.name, institution_id=operator.id, now=now
        )
        offered = await config.offered_effort_levels(found.id, session=s)
        await repo.insert_session(
            s,
            id=session_id,
            class_id=class_id,
            kind=CONTROL_TEST,
            game_settings=classic_settings().model_dump(mode="json"),
            ai_mode=(AiMode.llm if offered else AiMode.rule_based).value,
            debrief_mode=DEFAULT_DEBRIEF_MODE.value,
            inactivity_limit_hours=DEFAULT_INACTIVITY_LIMIT_HOURS,
            obligatory=DEFAULT_OBLIGATORY,
            required_share_percent=get_settings().completion_default_share_percent,
            model_config_id=found.id,
            effort_level=offered[0].name if offered else None,
            created_by=user.id,
            created_at=now,
        )
        await config.mark_referenced(found.id, session=s)
        await budget.set_budget(budget.BudgetScope.class_session(session_id), session=s)
        record = await pin_guide(s, session_id, body.scoring_guide_id, now)
        await audit.record(
            s,
            user.id,
            CONTROL_TEST_CREATED,
            {"class_session_id": session_id, "class_id": class_id},
            {
                "scoring_guide_id": str(record.id),
                "scoring_guide_version": record.version,
                "model_config_id": str(found.id),
                "institution_id": str(operator.id),
            },
            now,
        )
        await events.emit(s, "user", str(user.id))
    log.info(
        "control_test_created",
        class_session_id=str(session_id),
        class_id=str(class_id),
        scoring_guide_version=record.version,
        model_config_id=str(found.id),
    )
    default = await config.active_default()
    return ControlTestOut(
        id=session_id,
        class_id=class_id,
        name=classes.class_name(body.name)[0],
        institution_name=operator.name,
        created_at=now,
        scoring_guide=ControlTestGuideOut(
            id=record.id,
            version=record.version,
            edited=record.class_session_id is not None,
            draft=record.guide.status == "draft",
        ),
        ai_config=_config_out(found, default.id if default else None),
        can_open=True,
    )
