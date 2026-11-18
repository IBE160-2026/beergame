"""Render a mail from the Jinja2 templates (FR-72, AD-19).

Each kind has two templates in `templates/kinds/`: `<name>.txt.j2`, which also sets `subject`, and
`<name>.html.j2`. Both render the kind's own part only. `mail.txt.j2` and `mail.html.j2` put the
parts under the «ØL-spillet» heading: one part for an `immediate` mail, one per notice for a
digest, whose subject comes from `digest.txt.j2`. Templates get the recipient's `name` (may be
None), `url(path)` for a link on `PUBLIC_BASE_URL`, and the context the owning module returned.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from app.platform.config import get_settings

TEMPLATES = Path(__file__).parent / "templates"


@dataclass(frozen=True)
class Recipient:
    """Who a mail goes to, as the owning module resolves it at send time. Never stored or
    logged."""

    email: str
    name: str | None = None
    context: Mapping[str, object] = field(default_factory=dict)
    """Template variables of the kind (for example a link path), from the owning module."""


@dataclass(frozen=True)
class Section:
    """One notice's part of a mail: the kind's template name and its variables."""

    template: str
    context: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class Mail:
    to: str
    sender: str
    subject: str
    text: str
    html: str


@lru_cache
def environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(TEMPLATES),
        autoescape=select_autoescape(enabled_extensions=("html.j2",), default=False),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )


def _url(base: str):
    def url(path: str = "/") -> str:
        if not path.startswith("/"):
            raise ValueError("a link path starts with /")
        return base.rstrip("/") + path

    return url


def render(recipient: Recipient, sections: Sequence[Section], *, digest: bool) -> Mail:
    """The mail for `recipient` with one part per section; a digest takes its subject from
    `digest.txt.j2`, any other mail from its one kind's text template."""
    if not sections:
        raise ValueError("a mail has at least one part")
    if not digest and len(sections) != 1:
        raise ValueError("an immediate mail has exactly one part")
    settings = get_settings()
    env = environment()
    shared = {"name": recipient.name, "url": _url(settings.public_base_url)}
    texts, htmls = [], []
    subject = ""
    for section in sections:
        context = {**shared, **recipient.context, **section.context}
        text_template = env.get_template(f"kinds/{section.template}.txt.j2")
        module = text_template.make_module(context)
        subject = str(getattr(module, "subject", "")).strip()
        texts.append(str(module).strip())
        htmls.append(env.get_template(f"kinds/{section.template}.html.j2").render(context).strip())
    if digest:
        subject = str(env.get_template("digest.txt.j2").make_module(shared).subject).strip()
    if not subject:
        raise ValueError(f"template {sections[0].template!r} sets no subject")
    layout = {**shared, "subject": subject}
    return Mail(
        to=recipient.email,
        sender=settings.email_from,
        subject=subject,
        text=env.get_template("mail.txt.j2").render(layout, parts=texts),
        html=env.get_template("mail.html.j2").render(layout, parts=htmls),
    )
