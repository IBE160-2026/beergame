"""Story 2.13: the Norwegian descriptions of the AI player types (FR-33, FR-72, AD-19, C-4).

The texts are checked against the code they describe: the Rule-based text may name only the
inputs `engine.rule_based` reads, and every claim the LLM text makes about what the model is
told is checked on the rendered Story 2.4 prompts, the gateway's failure kinds and the Play
guard's parameter set. No database."""

import ast
import hashlib
import io
import re
import typing
from pathlib import Path

import pytest

from app import sim
from app.ai import gateway
from app.analysis import play_guard
from app.engine import rule_based
from app.modules.games.commands import DEFAULT_PLAY_GUARD_SET
from app.modules.games.service import OccupantKind
from app.modules.players import service
from app.modules.players.service import Description, describe
from app.platform.parameter_sets import read_parameter_set
from tests.players import test_llm_prompt as story_2_4

RULE_SOURCE = ast.parse(Path(rule_based.__file__).read_text(encoding="utf-8"))


def reads(name: str) -> set[str]:
    """The attributes `engine.rule_based` reads off the variable `name`."""
    return {
        node.attr
        for node in ast.walk(RULE_SOURCE)
        if isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == name
    }


def sentences(text: str) -> list[str]:
    return [part for part in re.split(r"(?<=[.:;])\s+|\n", text) if part.strip()]


RULE = describe("rule_based").text
LLM = describe("llm").text


# --- describe() -----------------------------------------------------------------------------


def test_describe_returns_each_text_with_its_version():
    rule = describe("rule_based")
    assert rule == Description(kind=OccupantKind.RULE_BASED, version=1, text=rule.text)
    assert rule.text.startswith("# Regelbasert KI-spiller\n")
    llm = describe(OccupantKind.LLM)
    assert (llm.kind, llm.version) == (OccupantKind.LLM, 1)
    assert llm.text.startswith("# LLM-spiller\n")
    assert describe("llm", version=1) == llm
    assert "\r" not in rule.text + llm.text


@pytest.mark.parametrize("kind", ["student", "scripted", "robot", ""])
def test_only_the_two_ai_player_types_have_a_description(kind):
    with pytest.raises(ValueError, match="no description for occupant kind"):
        describe(kind)


@pytest.mark.parametrize("version", [9, 0, True, 1.0, "1"])
def test_a_version_without_a_file_is_refused(version):
    with pytest.raises(ValueError, match="no description version"):
        describe("llm", version=version)


def test_the_newest_version_is_the_default(tmp_path, monkeypatch):
    for version, text in ((1, "en"), (2, "to"), (10, "ti")):
        (tmp_path / f"v{version}").mkdir()
        (tmp_path / f"v{version}" / "llm.md").write_text(text, encoding="utf-8")
    (tmp_path / "v11").mkdir()  # a newer folder without this kind's file
    (tmp_path / "v11" / "rule_based.md").write_text("elleve", encoding="utf-8")
    (tmp_path / "draft").mkdir()
    monkeypatch.setattr(service, "DESCRIPTIONS_DIR", tmp_path)
    assert (describe("llm").version, describe("llm").text) == (10, "ti")
    assert describe("llm", version=2).text == "to"
    assert describe("rule_based").version == 11


def test_no_file_at_all_is_a_value_error(tmp_path, monkeypatch):
    monkeypatch.setattr(service, "DESCRIPTIONS_DIR", tmp_path / "missing")
    with pytest.raises(ValueError, match="no description file for llm"):
        describe("llm")


SHIPPED = {
    "v1/rule_based.md": "ff0198bea9e932bf346e3f553eeaf33129148c7c9fd13d22cc651caaa3f659e3",
    "v1/llm.md": "25ce692320447197f03c58b5587ad0979f4e8ef2dfeeba3f196ef06d9e03e5dc",
}
"""sha256 of every shipped text (`\\r\\n` read as `\\n`). A shipped text is never edited: a
changed text is a new version folder, and its hash is added here."""


def test_shipped_texts_never_change():
    found = {
        path.relative_to(service.DESCRIPTIONS_DIR).as_posix()
        for path in service.DESCRIPTIONS_DIR.glob("v*/*.md")
    }
    assert found == set(SHIPPED)
    for name, digest in SHIPPED.items():
        text = (service.DESCRIPTIONS_DIR / name).read_text(encoding="utf-8")
        assert hashlib.sha256(text.replace("\r\n", "\n").encode()).hexdigest() == digest, name


# --- copy rules -----------------------------------------------------------------------------


@pytest.mark.parametrize("text", [RULE, LLM], ids=["rule_based", "llm"])
def test_the_texts_keep_the_copy_rules(text):
    assert not re.search(r"\bøl|øl\b|beer\s*game|bullwhip", text, re.IGNORECASE)
    assert "enheter" in text
    assert "bestilling" not in text  # the product says «ordre»
    assert len(text.split()) < 300  # short


# --- the Rule-based text against the rule ---------------------------------------------------

INPUT_TERMS = {
    "lager": "inventory",
    "restordre": "backlog",
    "innkommende ordre": "incoming_orders",
    "på vei": "supply_line",
    "tidligere ordre": "order_history",
    "nabo": "neighbour_numbers",
}
"""The Norwegian name of every `SeatView` input a description may name."""


def listed_inputs(text: str) -> list[str]:
    """The bullets after «… ser på disse tallene for sitt eget sete:»."""
    lines = text.splitlines()
    starts = [i for i, line in enumerate(lines) if line.endswith("sitt eget sete:")]
    assert len(starts) == 1, "the input list is missing"
    bullets = []
    for line in lines[starts[0] + 1 :]:
        if not line.startswith("- "):
            break
        bullets.append(line[2:].lower())
    return bullets


def test_the_rule_based_text_names_exactly_the_inputs_the_rule_reads():
    read = reads("seat_view") - {"role"}  # the Role only picks the delay
    named = set()
    for bullet in listed_inputs(RULE):
        fields = {field for term, field in INPUT_TERMS.items() if term in bullet}
        assert len(fields) == 1, (bullet, fields)
        (field,) = fields
        assert field in read, f"the rule does not read {field} ({bullet!r})"
        named.add(field)
    assert named == read == {"inventory", "backlog", "incoming_orders", "supply_line"}


def test_neighbour_numbers_and_costs_are_named_only_as_not_used():
    assert "neighbour_numbers" not in reads("seat_view")
    for sentence in sentences(RULE):
        if "nabo" in sentence.lower():
            assert "ikke" in sentence, sentence
    assert any("nabo" in sentence for sentence in sentences(RULE))
    settings_read = reads("settings")
    assert not {name for name in settings_read if "cost" in name or "rate" in name}
    assert "Kostnadene for lager og restordre inngår ikke i regelen." in RULE
    assert {"order_delay", "shipping_delay", "production_delay", "max_order"} <= settings_read
    assert "innstillingene som gjelder i spillet: forsinkelsene og største tillatte ordre" in RULE


def test_the_rule_based_text_names_its_rule_and_parameter_source():
    params = sim.load_rule_based_params(rule_based.DEFAULT_SET_ID)
    values = set(rule_based.RuleBasedParams.model_fields) - {"id", "version", "verified", "source"}
    numbers = {4: "fire"}
    assert f"Regelen har {numbers[len(values)]} parametere" in RULE
    assert "forankring og justering" in RULE
    assert "fast regel" in RULE
    assert "Sterman (1989)" in RULE
    # While the default set is a placeholder the text says so; a verified default needs a v2.
    assert ("ikke verifisert" in RULE) == (not params.verified)
    assert ("plassholderverdier" in RULE) == params.id.startswith("placeholder")


# --- the LLM text against the Story 2.4 prompt checks --------------------------------------


def test_the_llm_text_states_what_fr_33_asks():
    assert "Atferden varierer fra gang til gang" in LLM
    assert "Modellen får ikke vite at den spiller et spill." in LLM
    assert "kan spille bedre enn en typisk student" in LLM
    assert "legges den regelbaserte ordren inn i stedet, bare for den uken" in LLM
    assert "Spillvakten bytter setet til den regelbaserte spilleren for resten av spillet" in LLM


FAILURES = {
    "ikke svarer i tide": "timeout",
    "svaret ikke er en gyldig ordre": "invalid_output",
    "tjenesten som leverer modellen, gir en feil": "provider_error",
    "ikke er budsjett igjen til å spørre modellen": "budget_exhausted",
}


def test_the_llm_text_names_every_failure_that_places_the_rule_based_order():
    assert set(FAILURES.values()) == set(typing.get_args(gateway.FailureKind))
    for norwegian in FAILURES:
        assert norwegian in LLM, norwegian


def test_the_llm_text_describes_the_play_guard_set_in_use():
    params = play_guard.parse_params(
        read_parameter_set("play_guard", DEFAULT_PLAY_GUARD_SET), DEFAULT_PLAY_GUARD_SET
    )
    # Both limits of the band (`analysis/play_guard.md`): lower and upper.
    assert params.lower_share > 0 and params.upper_margin > 0
    assert "avviker for mye fra den regelbaserte ordren" in LLM
    assert "mistenkelig nær den nesten optimale ordren" in LLM
    assert ("Grensene er foreløpige og ikke kalibrert ennå." in LLM) == (not params.verified)


SHOWN = {
    "eget lager": "Inventory now:",
    "egen restordre": "Backlog now",
    "innkommende ordre": "$incoming_label:",
    "enheter på vei": "Units on their way to you:",
    "kostnadene": "Cost this week:",
    "sine egne tidligere uker": "Your earlier weeks",
}
"""Each number the LLM text lists, and the prompt line that shows it."""


def test_the_llm_text_does_not_contradict_the_prompt():
    template = (story_2_4.REAL_PROMPTS / "player_order" / "v1.md").read_text(encoding="utf-8")
    # «får ikke vite at den spiller et spill»: no game word in any prompt.
    assert "får ikke vite at den spiller et spill" in LLM
    assert "supply chain manager" in template
    story_2_4.test_the_prompt_text_frames_a_supply_chain_job_and_never_a_game()
    # «Hos forhandleren er innkommende ordre sluttkundenes etterspørsel».
    assert "Hos forhandleren er innkommende ordre sluttkundenes etterspørsel" in LLM
    story_2_4.test_customer_demand_only_in_the_retailer_prompt()
    # «ser ikke tallene til de andre leddene i kjeden».
    assert "ser ikke tallene til de andre leddene i kjeden" in LLM
    assert "You do not see the numbers of any other business." in template
    story_2_4.test_other_seats_numbers_never_reach_a_prompt()
    # «får ikke vite hvor mange uker som er igjen».
    assert "får ikke vite hvor mange uker som er igjen" in LLM
    assert "There is no last week" in template
    story_2_4.test_every_role_and_week_renders_without_a_week_count_or_future_demand()
    # The numbers it lists are the ones the prompt shows, one prompt line each.
    listed = re.search(r"tallene for sitt eget sete: ([^.]*)\.", LLM)
    assert listed is not None
    items = re.split(r", | og ", listed.group(1))
    assert items == list(SHOWN)
    for prompt_line in SHOWN.values():
        assert prompt_line in template, prompt_line
    # «et helt antall enheter mellom minste og største tillatte ordre».
    assert "et helt antall enheter mellom minste og største tillatte ordre" in LLM
    assert "a whole number from $min_order to $max_order" in template


# --- python -m app.sim describe -------------------------------------------------------------


def test_sim_describe_prints_both_descriptions(capsys):
    assert "describe" in sim.OFFLINE_COMMANDS
    assert sim.main(["describe"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("description rule_based v1\n# Regelbasert KI-spiller\n")
    assert "\ndescription llm v1\n# LLM-spiller\n" in out
    assert out.index("description rule_based") < out.index("description llm")
    assert RULE.strip() in out and LLM.strip() in out


def test_sim_describe_writes_utf_8_on_a_windows_console(monkeypatch):
    raw = io.BytesIO()
    console = io.TextIOWrapper(raw, encoding="cp1252")
    monkeypatch.setattr(sim.sys, "stdout", console)
    assert sim.main(["describe"]) == 0
    console.flush()
    out = raw.getvalue().decode("utf-8")
    assert "største tillatte ordre" in out and "språkmodell" in out
