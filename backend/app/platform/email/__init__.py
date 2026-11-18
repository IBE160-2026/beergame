"""Mail rendering and sending (AD-17, AD-19, FR-72, Story 3.5).

`render` builds a `Mail` from the Jinja2 templates in `templates/`: one text and one HTML part,
in Norwegian bokmål, headed «ØL-spillet», with links from `PUBLIC_BASE_URL`. `get_sender` picks
the `Sender`: Resend when `RESEND_API_KEY` is set, the deterministic `[email:mock]` sender when it
is not, outside production only. The provider sits behind the `Sender` protocol, so it can be
swapped without touching `messaging` (Issue #29).

`Recipient` is the shape an owning module's `service.py` returns when `messaging` asks it for an
address; it is never stored, logged or passed to a job. This package imports no module.
"""

from app.platform.email.render import Mail, Recipient, Section, render
from app.platform.email.senders import (
    MockSender,
    ResendSender,
    Sender,
    SendRefused,
    get_sender,
)

__all__ = [
    "Mail",
    "MockSender",
    "Recipient",
    "ResendSender",
    "Section",
    "SendRefused",
    "Sender",
    "get_sender",
    "render",
]
