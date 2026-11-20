"""Story 2.2: model configs (`ai.config`)."""

import json
import uuid
from decimal import Decimal

import psycopg
import pytest

from app.ai import config
from tests.ai.helpers import CONFIGS, MOCK, mock_config, query
from tests.conftest import libpq_dsn


def errors(data: object) -> list[tuple[str, str]]:
    with pytest.raises(config.ConfigInvalid) as caught:
        config.parse(data)
    return [(e.code, e.field) for e in caught.value.errors]


@pytest.mark.parametrize(
    "name", ["mock.json", "openrouter-deepseek.json", "openrouter-deepseek-eu.json"]
)
def test_the_shipped_configs_are_valid_and_marked_placeholder(name):
    spec = config.parse(json.loads((CONFIGS / name).read_text(encoding="utf-8")))
    assert spec.effort_levels and all(level.placeholder for level in spec.effort_levels)
    level = spec.effort_levels[0]
    assert (level.attempt_timeout_s, level.order_time_budget_s) == (4, 8)


def test_the_openrouter_config_names_the_variable_not_the_key():
    spec = config.parse(json.loads((CONFIGS / "openrouter-deepseek.json").read_text("utf-8")))
    assert spec.credential_env == "OPENROUTER_API_KEY"
    assert spec.model_version == "deepseek/deepseek-v4.1-flash-1017"
    assert spec.endpoint == "https://openrouter.ai/api/v1"
    eu = config.parse(json.loads((CONFIGS / "openrouter-deepseek-eu.json").read_text("utf-8")))
    assert (eu.endpoint, eu.region) == ("https://eu.openrouter.ai/api/v1", "eu")
    # Region and upstream provider are config data (Story 2.7): one ZDR endpoint, no fallback.
    for routed in (spec, eu):
        assert routed.routing is not None and routed.routing.router == "openrouter"
        assert routed.routing.order == ["nebius/fp8"] and routed.quantisation == "fp8"


@pytest.mark.parametrize(
    ("data", "field"),
    [
        (mock_config(api_key="abc"), "api_key"),
        (mock_config(**{"OpenAI-Api-Key": "abc"}), "OpenAI-Api-Key"),
        (
            mock_config(
                effort_levels=[{**MOCK["effort_levels"][0], "provider_params": {"token": "x"}}]
            ),
            "effort_levels.0.provider_params.token",
        ),
        (mock_config(quantisation="sk-or-v1-0123"), "quantisation"),
        (mock_config(endpoint="https://u:pw@host/v1"), "endpoint"),
        (mock_config(endpoint="https://host/v1?api_key=abc"), "endpoint"),
        (
            mock_config(
                effort_levels=[
                    {
                        **MOCK["effort_levels"][0],
                        "provider_params": {"headers": {"Authorization": "Bearer x"}},
                    }
                ]
            ),
            "effort_levels.0.provider_params.headers.Authorization",
        ),
    ],
)
def test_a_credential_in_the_file_is_refused_naming_the_field(data, field):
    assert errors(data) == [("credential_in_file", field)]


def test_a_prompt_version_without_a_file_is_refused():
    assert errors(mock_config(prompts={"player_order": 2})) == [
        ("prompt_missing", "prompts.player_order")
    ]
    assert config.parse(mock_config(prompts={"player_order": 1})).prompts == {"player_order": 1}


@pytest.mark.parametrize("missing", ["attempt_timeout_s", "order_time_budget_s"])
def test_an_effort_level_needs_both_time_values(missing):
    level = {k: v for k, v in MOCK["effort_levels"][0].items() if k != missing}
    assert errors(mock_config(effort_levels=[level])) == [("missing", f"effort_levels.0.{missing}")]


@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        ({"effort_levels": []}, [("too_short", "effort_levels")]),
        (
            {"effort_levels": [{**MOCK["effort_levels"][0], "attempt_timeout_s": 9}]},
            [("timeout_above_budget", "effort_levels.0.attempt_timeout_s")],
        ),
        (
            {"effort_levels": [MOCK["effort_levels"][0]] * 2},
            [("duplicate_name", "effort_levels.1.name")],
        ),
        ({"provider": "router"}, [("provider_unknown", "provider")]),
        ({"rate_limit_rpm": 0}, [("greater_than", "rate_limit_rpm")]),
        ({"rate_limit_rpm": 10**12}, [("less_than_equal", "rate_limit_rpm")]),
        (
            {"effort_levels": [{**MOCK["effort_levels"][0], "order_time_budget_s": float("inf")}]},
            [("finite_number", "effort_levels.0.order_time_budget_s")],
        ),
        (
            {"effort_levels": [{**MOCK["effort_levels"][0], "attempt_timeout_s": True}]},
            [("float_type", "effort_levels.0.attempt_timeout_s")],
        ),
        ({"prompts": {"Player": 1}}, [("string_pattern_mismatch", "prompts.Player.[key]")]),
        ({"surprise": 1}, [("extra_forbidden", "surprise")]),
        # The Klasseøkt's name and effect line of a level stay short (Story 5.5).
        *(
            (
                {"effort_levels": [{**MOCK["effort_levels"][0], key: value}]},
                [(code, f"effort_levels.0.{key}")],
            )
            for key, value, code in (
                ("label", "", "string_too_short"),
                ("label", "x" * 41, "string_too_long"),
                ("effect", "", "string_too_short"),
                ("effect", "x" * 201, "string_too_long"),
            )
        ),
        ({"credential_env": "OPENROUTER_API_KEY"}, [("credential_env_unused", "credential_env")]),
        (
            {"provider": "openai_compatible", "endpoint": "http://x"},
            [("endpoint_not_https", "endpoint"), ("missing", "credential_env")],
        ),
        (
            {"prices": {"input_usd_per_mtok": "-1", "output_usd_per_mtok": "0.000000001"}},
            [
                ("greater_than_equal", "prices.input_usd_per_mtok"),
                ("decimal_max_places", "prices.output_usd_per_mtok"),
            ],
        ),
    ],
)
def test_other_rules_name_the_field(changes, expected):
    assert errors(mock_config(**changes)) == expected


def test_ordinary_names_are_not_taken_for_credentials():
    level = {
        **MOCK["effort_levels"][0],
        "provider_params": {"prompt_cache_key": "x", "top_k": 5},
    }
    spec = config.parse(mock_config(effort_levels=[level], prompts={}))
    assert spec.effort_levels[0].provider_params["prompt_cache_key"] == "x"
    # Purpose names are checked by the schema, not by the credential scan.
    assert errors(mock_config(prompts={"order_token": 1})) == [
        ("prompt_missing", "prompts.order_token")
    ]


def test_a_config_is_one_object():
    assert errors([]) == [("not_an_object", "")]


async def test_add_stores_one_row_with_every_field(ai_db):
    spec = config.parse(mock_config(prompts={"player_order": 1}))
    row = await config.add(spec)
    assert row.id.version == 7 and not row.referenced and row.derived_from is None
    ((provider, endpoint, region, model, quant, cred, price_in, prompts, levels),) = query(
        ai_db,
        "SELECT provider, endpoint, region, model_version, quantisation, credential_env, "
        "input_usd_per_mtok, prompts, effort_levels FROM ai_model_configs",
    )
    assert (provider, endpoint, region, model, quant, cred) == (
        "mock",
        "mock://local",
        "local",
        "mock-1",
        "none",
        None,
    )
    assert price_in == Decimal("0.10000000")
    assert prompts == {"player_order": 1}
    assert levels == [
        {
            "name": "standard",
            "provider_params": {},
            "attempt_timeout_s": 4.0,
            "order_time_budget_s": 8.0,
            "max_output_tokens": 4096,
            "placeholder": True,
            # The Klasseøkt's name and effect line of the level (Story 5.5).
            "label": "Standard",
            "effect": "Testmodell: svarer straks og koster ingenting.",
        }
    ]
    assert await config.get(row.id) == row


async def test_a_referenced_config_cannot_change_and_an_edit_writes_a_new_row(ai_db):
    source = await config.add(config.parse(mock_config()))
    with psycopg.connect(libpq_dsn(ai_db)) as conn:
        for sql in (  # before it is referenced, only referenced_at may be set
            "UPDATE ai_model_configs SET model_version = 'other' WHERE id = %s",
            "UPDATE ai_model_configs SET referenced_at = now(), region = 'x' WHERE id = %s",
        ):
            with pytest.raises(psycopg.errors.RestrictViolation):
                conn.execute(sql, (source.id,))
            conn.rollback()
    referenced = await config.mark_referenced(source.id)
    assert referenced.referenced
    assert (await config.mark_referenced(source.id)).referenced_at == referenced.referenced_at
    before = query(ai_db, "SELECT * FROM ai_model_configs WHERE id = %s", (source.id,))
    with psycopg.connect(libpq_dsn(ai_db)) as conn:
        for sql in (
            "UPDATE ai_model_configs SET model_version = 'other' WHERE id = %s",
            "DELETE FROM ai_model_configs WHERE id = %s",
        ):
            with pytest.raises(psycopg.errors.RestrictViolation):
                conn.execute(sql, (source.id,))
            conn.rollback()
    edited = await config.derive(source.id, prompts={"player_order": 1})
    assert edited.id != source.id and edited.derived_from == source.id
    assert edited.spec.prompts == {"player_order": 1} and not edited.referenced
    assert query(ai_db, "SELECT * FROM ai_model_configs WHERE id = %s", (source.id,)) == before
    moved = await config.derive(edited.id, spec=config.parse(mock_config(name="renamed")))
    # `spec` is the whole new content, its prompts map included.
    assert moved.spec.name == "renamed" and moved.spec.prompts == {}
    assert moved.derived_from == edited.id
    assert [row.id for row in await config.list_all()] == [source.id, edited.id, moved.id]


async def test_an_edit_checks_the_prompt_file_and_the_source(ai_db):
    source = await config.add(config.parse(MOCK))
    with pytest.raises(config.ConfigInvalid):
        await config.derive(source.id, prompts={"player_order": 3})
    for missing in (uuid.uuid7(), "not-an-id"):
        with pytest.raises(config.ConfigNotFound):
            await config.derive(missing, prompts={"player_order": 1})
        with pytest.raises(config.ConfigNotFound):
            await config.mark_referenced(missing)
    assert len(await config.list_all()) == 1


@pytest.mark.parametrize(
    ("text", "expected"),
    [("player_order=1", ("player_order", 1)), ("debrief=v12", ("debrief", 12))],
)
def test_prompt_option(text, expected):
    assert config.parse_prompt(text) == expected


@pytest.mark.parametrize("text", ["player_order", "player_order=0", "Player=1", "x=v"])
def test_bad_prompt_option(text):
    with pytest.raises(ValueError):
        config.parse_prompt(text)
