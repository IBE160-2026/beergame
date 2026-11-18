"""Scrub personal data from free text before it reaches a provider (AD-6, C-1).

Each whole-word, case-insensitive match of a term (longest terms first, any whitespace between
its words) becomes `PLACEHOLDER`.
The offset map takes a span over the scrubbed text (what the model saw and may cite) back to
the original text; a span that touches a placeholder covers the whole original term.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass

PLACEHOLDER = "[REDACTED]"


@dataclass(frozen=True)
class Replacement:
    scrubbed_start: int
    scrubbed_end: int
    original_start: int
    original_end: int


@dataclass(frozen=True)
class OffsetMap:
    """From positions in the scrubbed text to positions in the original text."""

    scrubbed_length: int
    replacements: tuple[Replacement, ...]

    def _position(self, position: int, *, end: bool) -> int:
        shift = 0
        for r in self.replacements:
            if r.scrubbed_start < position < r.scrubbed_end:
                return r.original_end if end else r.original_start
            if r.scrubbed_end <= position:
                shift += (r.original_end - r.original_start) - (r.scrubbed_end - r.scrubbed_start)
        return position + shift

    def original_span(self, start: int, end: int) -> tuple[int, int]:
        """The original span for `scrubbed[start:end]`; raises `ValueError` outside the text."""
        if not 0 <= start <= end <= self.scrubbed_length:
            raise ValueError(f"span {start}..{end} is outside the scrubbed text")
        return self._position(start, end=False), self._position(end, end=True)


@dataclass(frozen=True)
class Scrubbed:
    text: str
    offsets: OffsetMap


def _pattern(term: str) -> str:
    """A term whose words may be separated by any whitespace (a double space, a newline)."""
    return r"\s+".join(re.escape(word) for word in term.split())


def scrub(text: str, terms: Iterable[str]) -> Scrubbed:
    words = sorted({t.strip() for t in terms if t.strip()}, key=lambda t: (-len(t), t))
    if not words:
        return Scrubbed(text, OffsetMap(len(text), ()))
    pattern = re.compile(
        r"(?<!\w)(?:" + "|".join(_pattern(word) for word in words) + r")(?!\w)", re.IGNORECASE
    )
    parts: list[str] = []
    replacements: list[Replacement] = []
    cursor = 0
    length = 0
    for match in pattern.finditer(text):
        parts.append(text[cursor : match.start()])
        length += match.start() - cursor
        replacements.append(
            Replacement(length, length + len(PLACEHOLDER), match.start(), match.end())
        )
        parts.append(PLACEHOLDER)
        length += len(PLACEHOLDER)
        cursor = match.end()
    parts.append(text[cursor:])
    scrubbed = "".join(parts)
    return Scrubbed(scrubbed, OffsetMap(len(scrubbed), tuple(replacements)))
