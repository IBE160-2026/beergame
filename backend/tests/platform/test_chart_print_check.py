"""The rules of the AD-18 chart PDF check (Story 6.7), without WeasyPrint: a mark 2 px off its
column, a font from outside the app and a clipped chart all fail it. The check itself runs against
the print page in `worker-batch` (CI e2e job)."""

import xml.etree.ElementTree as ET

from app.platform.chart_print_check import Mark, clipped, foreign, main, misaligned, svg_marks

COLUMNS = {10: 100.0, 11: 128.0}


def test_a_mark_within_one_px_of_its_column_passes():
    marks = [Mark("net", "position", 10, 100.9), Mark("cost", "cost", 11, 127.1)]
    assert misaligned(COLUMNS, marks) == []


def test_a_mark_two_px_off_or_without_a_column_fails():
    problems = misaligned(COLUMNS, [Mark("net", "net", 10, 102.0), Mark("net", "net", 12, 150.0)])
    assert len(problems) == 2
    assert "Uke 10 is at 102.00 px" in problems[0]
    assert "Uke 12 has no column" in problems[1]


def test_only_the_pages_own_origin_may_be_fetched():
    page = "http://frontend:3000/print/graf-over-tabell"
    urls = [
        page,
        "http://frontend:3000/_next/static/media/source-sans-3.woff2",
        "data:image/svg+xml;base64,AAAA",
        "https://fonts.gstatic.com/s/sourcesans3/v1/x.woff2",
        "https://frontend:3000/other-scheme.css",
    ]
    assert foreign(urls, page) == [urls[3], urls[4]]


def test_a_chart_outside_a_bound_is_clipped():
    assert clipped(10, 400, [("the page", 0, 643.7)]) == []
    assert clipped(10, 400.5, [("the page", 0, 400)]) == []  # within 1 px
    assert clipped(10, 420, [("the page", 0, 643.7), ("a div", 0, 400)]) == [
        "chart spans 10.00…420.00 px, outside a div 0.00…400.00 px"
    ]


def test_marks_are_read_from_rects_circles_groups_and_line_vertices():
    svg = ET.fromstring(
        '<svg xmlns="http://www.w3.org/2000/svg" width="100">'
        '<g data-mark="net" data-weeks="4 5" data-x="14 42"><path d="M0 0"/></g>'
        '<rect data-mark="position" data-week="4" x="12" y="0" width="4" height="4"/>'
        '<circle data-mark="now" data-week="5" cx="42" cy="1" r="3"/>'
        '<g data-mark="cost" data-week="5" data-x="42">'
        '<rect x="39" y="0" width="6" height="4"/></g>'
        '<g data-mark="cost" data-week="4" data-x="14"></g>'
        "</svg>"
    )
    assert list(svg_marks(svg)) == [
        ("net", 4, 14.0),
        ("net", 5, 42.0),
        ("position", 4, 14.0),
        ("now", 5, 42.0),
        ("cost", 5, 42.0),
        ("cost", 4, 14.0),
    ]


def test_main_exits_non_zero_on_any_problem(capsys):
    assert main(["http://x/print"], check=lambda url: []) == 0
    assert main(["http://x/print"], check=lambda url: ["the net chart is missing"]) == 1
    assert "FAIL the net chart is missing" in capsys.readouterr().out
    assert main([], check=lambda url: []) == 2
