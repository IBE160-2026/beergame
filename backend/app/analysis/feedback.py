"""Written feedback on one AI-assessed answer (Story 12.3, FR-54, NFR-9, AD-7).

The LLM writes no word of the shown text. Besides the overall score, its output
(`AssessmentFeedbackOutput`) holds one to four sentences, each naming an approved template and
filling its slots by reference only:

- a quote of the Student's answer as a character span over the scrubbed text the LLM saw
  (`quote`), which code maps back to the original text through the gateway's offset map;
- a Scoring guide criterion code of the item (`criterion`), which code renders with its text;
- for a sentence about the Student's game, fact ids of the item's stored facts set with a
  Debrief narration template (`analysis.narration`): Epic 9's validator checks it, and code renders
  every number and Week of it.

`validate_feedback` accepts an output only when every sentence keeps these rules and at least one
quotes the answer; `render_feedback` builds the stored text and its parts. Feedback templates hold
no digit, so every number shown comes from code, the pinned guide text or the Student's own words.

Pure (AD-1): stdlib, pydantic and `app.analysis` only."""

from collections.abc import Mapping, Sequence
from typing import Annotated, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from app.analysis.facts import FactSet
from app.analysis.narration import (
    NARRATION_TEMPLATES,
    AiSentence,
    AiTextOutput,
    NarrationTemplates,
    render_output,
    validate_ai_text,
)
from app.analysis.total import SCALE_TOP

__all__ = [
    "FEEDBACK_TEMPLATES",
    "MAX_FEEDBACK_SENTENCES",
    "MAX_QUOTE",
    "AssessmentFeedbackOutput",
    "FeedbackSentence",
    "FeedbackVerdict",
    "Span",
    "render_feedback",
    "template_lines",
    "validate_feedback",
]

_FROZEN = ConfigDict(frozen=True, extra="forbid")

MAX_FEEDBACK_SENTENCES = 4
"""The most sentences one item's feedback has."""

MAX_QUOTE = 300
"""The longest quote, in characters of the scrubbed text: a passage, not the whole answer."""

QUOTE = "quote"
CRITERION = "criterion"

FEEDBACK_TEMPLATES: Mapping[str, tuple[str, frozenset[str]]] = {
    # [ASSUMPTION] draft Norwegian copy for the founder's review; no digit may appear here.
    "quote-covers": (
        "Du skriver {quote}. Det svarer på kriteriet {criterion}.",
        frozenset({QUOTE, CRITERION}),
    ),
    "quote-lacks": (
        "Du skriver {quote}, men svaret forklarer ikke kriteriet {criterion}.",
        frozenset({QUOTE, CRITERION}),
    ),
    "missing": (
        "Svaret tar ikke opp kriteriet {criterion}.",
        frozenset({CRITERION}),
    ),
}
"""The approved feedback sentences: id → (text, the slots it takes)."""


class Span(BaseModel):
    """A passage of the answer as the LLM saw it: characters `start` up to, not including, `end`."""

    model_config = _FROZEN

    start: Annotated[int, Field(ge=0)]
    end: Annotated[int, Field(ge=0)]


class FeedbackSentence(BaseModel):
    """One feedback sentence: a template id and what fills its slots, by reference only."""

    model_config = _FROZEN

    template_id: Annotated[str, Field(min_length=1, max_length=60)]
    quote: Span | None = None
    criterion: Annotated[str, Field(min_length=1, max_length=20)] | None = None
    fact_ids: Annotated[
        tuple[Annotated[str, Field(min_length=1, max_length=80)], ...], Field(max_length=3)
    ] = ()


class AssessmentFeedbackOutput(BaseModel):
    """What the LLM answers for one item from prompt `assessment/v2` on: the overall score on the
    five-step scale (never per criterion) and the feedback sentences."""

    model_config = ConfigDict(extra="forbid")

    score: Annotated[int, Field(ge=0, le=SCALE_TOP)]
    feedback: Annotated[
        tuple[FeedbackSentence, ...], Field(min_length=1, max_length=MAX_FEEDBACK_SENTENCES)
    ]


Reason = Literal[
    "unknown_template",
    "wrong_arity",
    "span_out_of_range",
    "unknown_criterion",
    "no_quote",
    "repeated",
    "unknown_fact",
    "not_applicable",
    "number_outside_facts",
]


class FeedbackVerdict(BaseModel):
    """`validate_feedback`'s answer: accepted, or the reason it was not."""

    model_config = _FROZEN

    accepted: bool
    reason: Reason | None = None


class OffsetMap(Protocol):
    """The gateway's offset map (the scrubber's `OffsetMap`), seen from here: what this pure
    module needs of it."""

    scrubbed_length: int

    def original_span(self, start: int, end: int) -> tuple[int, int]: ...


def _slots(sentence: FeedbackSentence) -> frozenset[str]:
    found = set()
    if sentence.quote is not None:
        found.add(QUOTE)
    if sentence.criterion is not None:
        found.add(CRITERION)
    return frozenset(found)


def _is_fact(sentence: FeedbackSentence) -> bool:
    return sentence.template_id in NARRATION_TEMPLATES


def _passage(answer: str, start: int, end: int) -> tuple[int, int]:
    """The quoted passage of the original answer: whole words only (a span that starts or ends
    inside a word takes in the whole word, since a model counts characters approximately), with
    its edge whitespace left out."""
    while 0 < start < len(answer) and answer[start - 1].isalnum() and answer[start].isalnum():
        start -= 1
    while 0 < end < len(answer) and answer[end - 1].isalnum() and answer[end].isalnum():
        end += 1
    while start < end and answer[start].isspace():
        start += 1
    while end > start and answer[end - 1].isspace():
        end -= 1
    return start, end


def validate_feedback(
    output: AssessmentFeedbackOutput,
    answer: str,
    offsets: OffsetMap,
    criteria: Sequence[str],
    fact_set: FactSet | None,
    narration_templates: NarrationTemplates | None,
) -> FeedbackVerdict:
    """Accept the feedback only when every sentence names an approved template with exactly its
    slots, every quote is a span of at most `MAX_QUOTE` characters inside the scrubbed answer the
    LLM saw (`offsets.scrubbed_length`) whose passage of the original `answer` is not blank,
    every criterion is one of the item's codes, no sentence
    repeats, at least one quotes the answer, and the sentences about the Student's game pass the
    Debrief's AI-text validator on the item's own stored facts set (FR-54, NFR-9, AD-7)."""
    seen: set[str] = set()
    facts: list[AiSentence] = []
    quoted = False
    for sentence in output.feedback:
        key = sentence.model_dump_json()
        if key in seen:
            return FeedbackVerdict(accepted=False, reason="repeated")
        seen.add(key)
        if _is_fact(sentence):
            if _slots(sentence):
                return FeedbackVerdict(accepted=False, reason="wrong_arity")
            if fact_set is None or narration_templates is None or not sentence.fact_ids:
                return FeedbackVerdict(accepted=False, reason="unknown_fact")
            facts.append(AiSentence(template_id=sentence.template_id, fact_ids=sentence.fact_ids))
            continue
        template = FEEDBACK_TEMPLATES.get(sentence.template_id)
        if template is None:
            return FeedbackVerdict(accepted=False, reason="unknown_template")
        if _slots(sentence) != template[1] or sentence.fact_ids:
            return FeedbackVerdict(accepted=False, reason="wrong_arity")
        if sentence.quote is not None:
            start, end = sentence.quote.start, sentence.quote.end
            if not (start < end <= offsets.scrubbed_length) or end - start > MAX_QUOTE:
                return FeedbackVerdict(accepted=False, reason="span_out_of_range")
            first, last = _passage(answer, *offsets.original_span(start, end))
            if first >= last:
                return FeedbackVerdict(accepted=False, reason="span_out_of_range")
            quoted = True
        if sentence.criterion is not None and sentence.criterion not in criteria:
            return FeedbackVerdict(accepted=False, reason="unknown_criterion")
    if facts:
        assert fact_set is not None and narration_templates is not None
        verdict = validate_ai_text(
            AiTextOutput(sentences=tuple(facts)), fact_set, narration_templates
        )
        if not verdict.accepted:
            return FeedbackVerdict(accepted=False, reason=verdict.reason)
    if not quoted:
        return FeedbackVerdict(accepted=False, reason="no_quote")
    return FeedbackVerdict(accepted=True)


type Part = dict[str, str | list[int]]
"""`{"text": …}` or `{"quote": [start, end]}` over the original answer."""


def render_feedback(
    output: AssessmentFeedbackOutput,
    answer: str,
    offsets: OffsetMap,
    criteria: Mapping[str, str],
    fact_set: FactSet | None,
    narration_templates: NarrationTemplates | None,
) -> tuple[str, list[Part]]:
    """The text and parts of feedback `validate_feedback` accepted: each quote mapped through
    `offsets` to the Student's original `answer` (its edge whitespace trimmed), each criterion as
    `code (text)` from `criteria`, each sentence about the game rendered by the narration's code.
    The text shows a quote as «…»; the parts keep the span, so a view renders it from the answer."""
    parts: list[Part] = []
    text: list[str] = []

    def add(chunk: str) -> None:
        if not chunk:
            return
        if parts and "text" in parts[-1]:
            parts[-1]["text"] = f"{parts[-1]['text']}{chunk}"
        else:
            parts.append({"text": chunk})
        text.append(chunk)

    for n, sentence in enumerate(output.feedback):
        if n:
            add(" ")
        if _is_fact(sentence):
            assert fact_set is not None and narration_templates is not None
            one = AiTextOutput(
                sentences=(
                    AiSentence(template_id=sentence.template_id, fact_ids=sentence.fact_ids),
                )
            )
            add(render_output(one, fact_set, narration_templates).text)
            continue
        template, _ = FEEDBACK_TEMPLATES[sentence.template_id]
        criterion = ""
        if sentence.criterion is not None:
            criterion = f"{sentence.criterion} ({criteria.get(sentence.criterion, '')})"
        before, _, after = template.partition("{quote}")
        if sentence.quote is None:
            add(template.format(criterion=criterion))
            continue
        add(before.format(criterion=criterion))
        start, end = _passage(
            answer, *offsets.original_span(sentence.quote.start, sentence.quote.end)
        )
        if after[:1] in ".," and end - start > 1 and answer[end - 1] == ".":
            # The sentence goes on after the quote: its own full stop is the template's.
            end -= 1
        parts.append({"quote": [start, end]})
        text.append(f"«{answer[start:end]}»")
        add(after.format(criterion=criterion))
    return "".join(text), parts


def template_lines(narration_templates: NarrationTemplates | None) -> str:
    """The templates a feedback may use, one per line for the prompt: the feedback sentences with
    their slots, then the narration templates (with how many facts each takes) when the item has
    facts."""
    lines = [
        f"{template_id} ({', '.join(sorted(slots))}): {text}"
        for template_id, (text, slots) in FEEDBACK_TEMPLATES.items()
    ]
    if narration_templates is not None:
        lines += narration_templates.lines(NARRATION_TEMPLATES)
    return "\n".join(lines)
