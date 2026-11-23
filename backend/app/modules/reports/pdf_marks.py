"""The machine-readable mark on AI-generated text in the tagged Student report (Story 13.10, FR-34,
UX-DR69, AD-18).

The print route marks every AI-generated text with `data-ai-generated="true"` on its `<p>` or
`<span>` (taken from `ai_generated` only), beside the prefix «KI-generert, kan ta feil:» people
read. WeasyPrint's PDF/UA tagging carries no attribute of the HTML into the structure tree, so
`install()` wraps the one function that builds a structure element per box
(`weasyprint.pdf.tags._build_box_tree`, WeasyPrint 70): the structure element of a marked `p` or
`span` gets the attribute object `<< /O /UserProperties /P [<< /N (ai_generated) /V true >>] >>`
(ISO 32000-1, 14.8.5.8), and the catalog's `MarkInfo` says the file holds user properties. A
reader, a validator or a script finds AI text in the PDF by that property alone.

Only these two elements are marked, so a table cell's own attribute object (its headers) is never
touched; an attribute object a later WeasyPrint might give them is kept beside the property.
`install()` is idempotent and checks that WeasyPrint still has the function it wraps:
a WeasyPrint without it fails the render loudly instead of dropping the mark."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

__all__ = ["AI_PROPERTY", "MARKED", "install", "mark_catalog"]

AI_PROPERTY = "ai_generated"
MARKED = frozenset({"p", "span"})
"""The HTML elements whose `data-ai-generated="true"` becomes the property."""

_WRAPPED = "_olspillet_ai_marks"
_USED = "_olspillet_ai_marked"


def _marked(box: Any) -> bool:
    element = getattr(box, "element", None)
    return (
        element is not None
        and getattr(box, "element_tag", None) in MARKED
        and element.get("data-ai-generated") == "true"
    )


def _user_properties(pydyf: Any) -> Any:
    return pydyf.Dictionary(
        {
            "O": "/UserProperties",
            "P": pydyf.Array([pydyf.Dictionary({"N": pydyf.String(AI_PROPERTY), "V": "true"})]),
        }
    )


def wrap(build: Callable[..., Iterator[Any]], pydyf: Any) -> Callable[..., Iterator[Any]]:
    """`build` (WeasyPrint's `_build_box_tree`) with the property added to each structure element
    it yields for a marked box. A marked `p` or `span` yields its own element (one per line or page
    fragment); WeasyPrint looks the function up by name when it recurses, so every box passes
    through here."""

    def marked(box: Any, parent: Any, pdf: Any, *args: Any, **kwargs: Any) -> Iterator[Any]:
        source = getattr(box, "_box", box)
        ai = _marked(source)
        for element in build(box, parent, pdf, *args, **kwargs):
            if ai:
                properties = _user_properties(pydyf)
                own = element.get("A")
                # An element's own attribute objects are kept beside the property (an array of
                # attribute objects, ISO 32000-1, 14.7.5).
                if own is None:
                    element["A"] = properties
                elif isinstance(own, list):
                    own.append(properties)
                else:
                    element["A"] = pydyf.Array([own, properties])
                setattr(pdf, _USED, True)
            yield element

    setattr(marked, _WRAPPED, True)
    return marked


def mark_catalog(pdf: Any, pydyf: Any) -> None:
    """The finisher's half: `MarkInfo` gains `/UserProperties true` when a property was added,
    and only then (a report without AI text uses none)."""
    if not getattr(pdf, _USED, False):
        return
    info = pdf.catalog.get("MarkInfo")
    if info is None:
        info = pydyf.Dictionary({"Marked": "true"})
        pdf.catalog["MarkInfo"] = info
    info["UserProperties"] = "true"


def install() -> None:
    """Wrap WeasyPrint's structure builder once (needs WeasyPrint: only where it runs)."""
    import pydyf
    from weasyprint.pdf import tags

    build = getattr(tags, "_build_box_tree", None)
    if build is None or not callable(build):
        raise RuntimeError("WeasyPrint has no _build_box_tree: the AI mark cannot be added")
    if getattr(build, _WRAPPED, False):
        return
    tags._build_box_tree = wrap(build, pydyf)
