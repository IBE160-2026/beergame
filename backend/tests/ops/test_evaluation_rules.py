"""The pure parts of the evaluation export (Story 15.4, FR-71, FR-77, AD-12, AD-14): the policy,
the deletion date and the pseudonym. No database."""

import uuid
from datetime import UTC, date, datetime

from app.modules.ops import evaluation
from app.platform import authz, retention

KEY = "Nøkkelholder-K7q2-evaluering-2026-wXyZ-0123456789"
OTHER_KEY = "En-helt-annen-nøkkel-for-evaluering-abcdefghij"


def test_the_policy_holds_only_for_an_admin_and_an_agreement():
    class User:
        def __init__(self, *roles: str) -> None:
            self.id = uuid.uuid7()
            self.roles = frozenset(roles)

    session = uuid.uuid7()
    admin, lecturer = User(authz.ADMIN), User(authz.LECTURER)
    with_agreement = evaluation.ExportResource(session, agreement_recorded=True)
    without = evaluation.ExportResource(session, agreement_recorded=False)
    assert authz.can(admin, "export_pseudonymised", with_agreement)
    assert not authz.can(admin, "export_pseudonymised", without)
    assert not authz.can(lecturer, "export_pseudonymised", with_agreement)
    assert not authz.can(admin, "export_pseudonymised", object())


def test_the_deletion_date_is_six_calendar_months_after_the_test_deadline():
    assert retention.add_months(date(2026, 8, 31), 6) == date(2027, 2, 28)
    assert retention.add_months(date(2026, 1, 15), 6) == date(2026, 7, 15)
    assert retention.deletion_date(None, 6) is None


def test_the_pseudonym_is_the_hmac_of_the_user_id_and_never_the_fingerprint():
    user = uuid.UUID("01900000-0000-7000-8000-000000000001")
    assert evaluation.pseudonym(KEY, user) == evaluation.pseudonym(KEY, user)
    assert evaluation.pseudonym(KEY, user) != evaluation.pseudonym(OTHER_KEY, user)
    assert len(evaluation.pseudonym(KEY, user)) == 64
    assert evaluation.fingerprint(KEY) not in {evaluation.pseudonym(KEY, user)}


def test_the_deletion_date_is_read_on_the_oslo_calendar():
    # 22:30 UTC on 31 August is 1 September in Oslo: six months on is 1 March.
    late = datetime(2026, 8, 31, 22, 30, tzinfo=UTC)
    assert retention.deletion_date(late, 6) == date(2027, 3, 1)


def test_a_text_a_spreadsheet_would_run_gets_a_leading_quote():
    assert evaluation.cell("=HYPERLINK(1)") == "'=HYPERLINK(1)"
    assert evaluation.cell("-1 for lite") == "'-1 for lite"
    assert evaluation.cell("Jeg bestilte 8.") == "Jeg bestilte 8."
    assert evaluation.cell(-3) == "-3"
