"""The AD-18 chart spike's PDF check (Story 6.7).

Converts the internal print page of Graf over tabell (`frontend` `/print/graf-over-tabell`) with
WeasyPrint in its `pdf/ua-1` variant, as the Student report will be (Epic 13), and fails if

- a chart (`svg[data-chart]`) is missing, has no `<title>` (the only alternative text WeasyPrint
  reads), or is clipped by the page or by an ancestor that hides overflow;
- any Week mark (`data-mark` with `data-week`) is more than 1 px off the centre of its table
  column (`th[scope=col][data-col]`), in WeasyPrint's own layout;
- the conversion fetched anything (a font above all) from outside the page's origin.

Run where WeasyPrint and Pango are installed, the `worker-batch` image:
`python -m app.platform.chart_print_check http://frontend:3000/print/graf-over-tabell`.
The geometry and fetch rules are plain functions, tested without WeasyPrint.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

TOLERANCE = 1.0
"""Px a mark may be off its column's centre (AD-18)."""

SVG = "{http://www.w3.org/2000/svg}"


@dataclass(frozen=True)
class Mark:
    chart: str
    kind: str
    week: int
    x: float


def misaligned(columns: dict[int, float], marks: Iterable[Mark]) -> list[str]:
    """Each mark more than `TOLERANCE` px off its column's centre, or with no column at all."""
    problems = []
    for mark in marks:
        centre = columns.get(mark.week)
        if centre is None:
            problems.append(f"{mark.chart} {mark.kind} mark in Uke {mark.week} has no column")
        elif abs(mark.x - centre) > TOLERANCE:
            problems.append(
                f"{mark.chart} {mark.kind} mark in Uke {mark.week} is at {mark.x:.2f} px, "
                f"its column's centre at {centre:.2f} px"
            )
    return problems


def origin(url: str) -> tuple[str, str]:
    parts = urlsplit(url)
    return parts.scheme, parts.netloc


def foreign(urls: Iterable[str], page: str) -> list[str]:
    """Every fetched URL outside the page's origin; inline `data:` URLs are part of the page."""
    home = origin(page)
    return [url for url in urls if not url.startswith("data:") and origin(url) != home]


def clipped(left: float, right: float, bounds: Iterable[tuple[str, float, float]]) -> list[str]:
    """Each bound `(name, left, right)` that does not hold the horizontal span `left`…`right`."""
    return [
        f"chart spans {left:.2f}…{right:.2f} px, outside {name} {low:.2f}…{high:.2f} px"
        for name, low, high in bounds
        if left < low - TOLERANCE or right > high + TOLERANCE
    ]


def svg_marks(svg: Any) -> Iterator[tuple[str, int, float]]:
    """`(kind, week, x)` of each Week mark in an SVG element tree, in the SVG's own units: a
    rect's centre, a circle's `cx`, or each `data-x` of a group listing `data-weeks` (a line's
    vertices)."""
    for element in svg.iter():
        kind = element.get("data-mark")
        if not kind:
            continue
        if element.get("data-weeks") is not None:
            weeks = element.get("data-weeks").split()
            xs = element.get("data-x", "").split()
            for week, x in zip(weeks, xs, strict=True):
                yield kind, int(week), float(x)
            continue
        week = element.get("data-week")
        if week is None:
            continue
        tag = element.tag.removeprefix(SVG)
        if tag == "rect":
            yield kind, int(week), float(element.get("x")) + float(element.get("width")) / 2
        elif tag == "circle":
            yield kind, int(week), float(element.get("cx"))
        else:  # a group: each of its rects, or its own `data-x`
            rects = [child for child in element if child.tag.removeprefix(SVG) == "rect"]
            for rect in rects:
                yield kind, int(week), float(rect.get("x")) + float(rect.get("width")) / 2
            if not rects and element.get("data-x") is not None:
                yield kind, int(week), float(element.get("data-x"))


def _boxes(box: Any, ancestors: tuple[Any, ...] = ()) -> Iterator[tuple[Any, tuple[Any, ...]]]:
    yield box, ancestors
    for child in getattr(box, "children", None) or ():
        yield from _boxes(child, (*ancestors, box))


def check(page_url: str) -> list[str]:
    """Every problem with the print page's charts in WeasyPrint's PDF (empty when all is well)."""
    from weasyprint import HTML, URLFetcher  # needs Pango: only where it runs

    fetched: list[str] = []

    class Recording(URLFetcher):
        """Fetches as WeasyPrint does, keeping each URL; a failed fetch fails the check."""

        def fetch(self, url: str, headers: Any = None) -> Any:
            fetched.append(url)
            return super().fetch(url, headers)

    fetcher = Recording(fail_on_errors=True)
    document = HTML(url=page_url, url_fetcher=fetcher).render(pdf_variant="pdf/ua-1")
    problems = [f"fetched from outside the app: {url}" for url in foreign(fetched, page_url)]
    if not any(re.search(r"\.woff2?(\?|$)", url) for url in fetched):
        problems.append("no font was fetched from the app")
    if len(document.pages) != 1:
        problems.append(f"the page broke over {len(document.pages)} PDF pages")

    columns: dict[int, float] = {}
    charts: list[tuple[Any, tuple[Any, ...]]] = []
    for page in document.pages:
        for box, ancestors in _boxes(page._page_box):
            element = getattr(box, "element", None)
            if element is None or getattr(box, "element_tag", None) is None:
                continue
            tag = box.element_tag
            # The cell itself: WeasyPrint's anonymous line and text boxes inside it carry the same
            # element and tag, and would put the column at the glyphs' centre.
            is_cell = type(box).__name__ == "TableCellBox" and tag == "th"
            if is_cell and element.get("scope") == "col" and element.get("data-col"):
                columns[int(element.get("data-col"))] = box.border_box_x() + box.border_width() / 2
            elif tag == f"{SVG}svg" and element.get("data-chart") and hasattr(box, "replacement"):
                charts.append((box, ancestors))

    drawn = {box.element.get("data-chart") for box, _ in charts}
    for wanted in ("net", "cost"):
        if wanted not in drawn:
            problems.append(f"the {wanted} chart is missing")
    if not columns:
        problems.append("no week columns in the table")

    marks: list[Mark] = []
    for box, ancestors in charts:
        element = box.element
        chart = element.get("data-chart")
        title = element.find(f"{SVG}title")
        if title is None or not (title.text or "").strip():
            problems.append(f"the {chart} chart has no <title>")
        left = box.content_box_x()
        width = box.width
        declared = float(element.get("width") or width)
        if width <= 0 or box.height <= 0:
            problems.append(f"the {chart} chart has no size")
            continue
        scale = width / declared
        page_box = ancestors[0]
        bounds = [("the page", page_box.content_box_x(), page_box.content_box_x() + page_box.width)]
        bounds += [
            (
                f"a {ancestor.element_tag} that hides overflow",
                ancestor.padding_box_x(),
                ancestor.padding_box_x() + ancestor.padding_width(),
            )
            for ancestor in ancestors[1:]
            if ancestor.style["overflow"] != "visible"
        ]
        problems += [f"the {chart} chart: {p}" for p in clipped(left, left + width, bounds)]
        if chart == "axis":
            continue
        for kind, week, x in svg_marks(element):
            marks.append(Mark(chart, kind, week, left + x * scale))
    if not marks and charts:
        problems.append("the charts have no Week marks")
    problems += misaligned(columns, marks)
    if not document.write_pdf(pdf_variant="pdf/ua-1"):  # the conversion itself must succeed
        problems.append("WeasyPrint wrote no PDF")
    return problems


def main(argv: list[str], check: Callable[[str], list[str]] = check) -> int:
    if len(argv) != 1:
        print("usage: python -m app.platform.chart_print_check <print page url>", file=sys.stderr)
        return 2
    problems = check(argv[0])
    for problem in problems:
        print(f"FAIL {problem}")
    if not problems:
        print(f"ok: charts in line with their columns in WeasyPrint's pdf/ua-1 of {argv[0]}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
