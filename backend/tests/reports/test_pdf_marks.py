"""Story 13.10 (FR-34, UX-DR69): the machine-readable mark on AI text in the tagged PDF.

`pdf_marks.wrap` adds the `/UserProperties` attribute `ai_generated` to the structure element of
a `p` or `span` the print route marked `data-ai-generated="true"`, and to nothing else; the
finisher says in `MarkInfo` that the file uses user properties. WeasyPrint's own builder is
stood in for by a generator that yields one structure element per box, as it does; the real
render is checked on the e2e sample (`student-report.spec.ts`, veraPDF)."""

import pydyf

from app.modules.reports import pdf_marks


class Element:
    def __init__(self, attributes: dict[str, str]) -> None:
        self.attributes = attributes

    def get(self, name: str) -> str | None:
        return self.attributes.get(name)


class Box:
    def __init__(self, tag: str, **attributes: str) -> None:
        self.element_tag = tag
        self.element = Element(attributes)


class Placeholder:
    """WeasyPrint's `AbsolutePlaceholder`: the box it stands for is `_box`."""

    def __init__(self, box: Box) -> None:
        self._box = box


class Pdf:
    def __init__(self) -> None:
        self.catalog = pydyf.Dictionary({"MarkInfo": pydyf.Dictionary({"Marked": "true"})})


def build(box, parent, pdf, *rest):
    yield pydyf.Dictionary({"S": "/X", "K": pydyf.Array([])})


def test_only_a_marked_paragraph_or_span_gets_the_property():
    wrapped = pdf_marks.wrap(build, pydyf)
    marked = [
        Box("p", **{"data-ai-generated": "true"}),
        Box("span", **{"data-ai-generated": "true"}),
        Placeholder(Box("span", **{"data-ai-generated": "true"})),
    ]
    for box in marked:
        pdf = Pdf()
        [element] = wrapped(box, None, pdf)
        properties = element["A"]
        assert properties["O"] == "/UserProperties"
        [prop] = properties["P"]
        assert (str(prop["N"].string), prop["V"]) == ("ai_generated", "true")
        pdf_marks.mark_catalog(pdf, pydyf)
        assert pdf.catalog["MarkInfo"]["UserProperties"] == "true"
    for box in (
        Box("p"),
        Box("p", **{"data-ai-generated": "false"}),
        Box("div", **{"data-ai-generated": "true"}),
        Box("td", **{"data-ai-generated": "true"}),
    ):
        pdf = Pdf()
        [element] = wrapped(box, None, pdf)
        assert "A" not in element
        # Nothing marked: the catalog claims no user properties.
        pdf_marks.mark_catalog(pdf, pydyf)
        assert "UserProperties" not in pdf.catalog["MarkInfo"]


def test_an_element_with_its_own_attributes_keeps_them_beside_the_property():
    def with_attributes(box, parent, pdf, *rest):
        yield pydyf.Dictionary({"S": "/P", "A": pydyf.Dictionary({"O": "/Layout"})})

    box = Box("p", **{"data-ai-generated": "true"})
    [element] = pdf_marks.wrap(with_attributes, pydyf)(box, None, Pdf())
    own, added = element["A"]
    assert (own["O"], added["O"]) == ("/Layout", "/UserProperties")
