"""Story 2.3: scrubbing free text and the offset map (AD-6, C-1)."""

import uuid

import pytest

from app.ai.budget import BudgetScope
from app.ai.scrub import PLACEHOLDER, scrub
from app.platform import pii

TEXT = "Ola Nordmann (ola@uni.no, 123456) ordered; ola nordmann again. Olav stays."
TERMS = ["Ola Nordmann", "ola@uni.no", "123456", "Ola"]


def test_terms_become_placeholders_longest_first_and_whole_words_only():
    result = scrub(TEXT, TERMS)
    assert result.text == (
        f"{PLACEHOLDER} ({PLACEHOLDER}, {PLACEHOLDER}) ordered; {PLACEHOLDER} again. Olav stays."
    )


def test_the_offset_map_takes_a_scrubbed_span_back_to_the_original():
    result = scrub(TEXT, TERMS)
    offsets = result.offsets
    # A span of plain text after three placeholders.
    start = result.text.index("ordered")
    o_start, o_end = offsets.original_span(start, start + len("ordered"))
    assert TEXT[o_start:o_end] == "ordered"
    # A whole placeholder maps to the whole term.
    start = result.text.index(PLACEHOLDER, start)
    o_start, o_end = offsets.original_span(start, start + len(PLACEHOLDER))
    assert TEXT[o_start:o_end] == "ola nordmann"
    # A span cutting into a placeholder covers the whole term.
    o_start, o_end = offsets.original_span(3, len(result.text))
    assert TEXT[o_start:o_end] == TEXT
    o_start, o_end = offsets.original_span(0, 4)
    assert TEXT[o_start:o_end] == "Ola Nordmann"
    assert offsets.original_span(0, 0) == (0, 0)
    end = len(result.text)
    assert offsets.original_span(end, end) == (len(TEXT), len(TEXT))


def test_a_span_outside_the_scrubbed_text_is_refused():
    offsets = scrub(TEXT, TERMS).offsets
    with pytest.raises(ValueError):
        offsets.original_span(5, 4)
    with pytest.raises(ValueError):
        offsets.original_span(0, offsets.scrubbed_length + 1)


def test_no_terms_leave_the_text_and_map_unchanged():
    result = scrub(TEXT, ["", "  "])
    assert result.text == TEXT
    assert result.offsets.original_span(4, 12) == (4, 12)


async def test_an_evaluation_scope_has_no_terms():
    assert await pii.terms(BudgetScope.evaluation(uuid.uuid4())) == []


def test_the_words_of_a_term_may_be_split_by_any_whitespace():
    assert scrub("ola\n nordmann wrote", ["Ola Nordmann"]).text == f"{PLACEHOLDER} wrote"


def test_a_genitive_any_address_and_a_long_number_are_scrubbed_with_any_term():
    """Story 9.15: «Karis» is Kari's; an address or a student number no term names is scrubbed
    too once there are terms (a Class session). A Week or an Order stays."""
    text = "Karis svar, per@annen.no og 2401177 i uke 12 med 40 varer."
    assert scrub(text, ["Kari"]).text == (
        f"{PLACEHOLDER} svar, {PLACEHOLDER} og {PLACEHOLDER} i uke 12 med 40 varer."
    )
    assert scrub(text, []).text == text  # an evaluation scope: no terms, nothing scrubbed
