"""Mail senders behind one protocol (AD-17, Issue #29).

- `ResendSender` posts to Resend's HTTP API with the stdlib (no SDK; `app/platform` loads no
  HTTP client library). The `Idempotency-Key` is the delivery id, so a retried send after a
  crash between the provider's answer and our commit is dropped by the provider.
- `MockSender` logs one `[email:mock]` line with ids only and returns `mock-<key>`, the same
  every time for the same key. It keeps the mails it got in memory (`sent`) for tests.

`get_sender()` picks Resend when `RESEND_API_KEY` is set, the mock when it is not outside
production, and refuses in production without a key. Another provider is one more class here.
"""

import asyncio
import json
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Protocol

import structlog

from app.platform.config import Settings, get_settings
from app.platform.email.render import Mail

log = structlog.get_logger(__name__)

RESEND_URL = "https://api.resend.com/emails"
RESEND_TIMEOUT_S = 10

Transport = Callable[[str, dict[str, str], bytes], tuple[int, bytes]]
"""`(url, headers, body) -> (status, body)`: one blocking POST."""


class SendRefused(RuntimeError):
    """The mail was not handed to a provider. The message is a code, never an address."""


class Sender(Protocol):
    async def send(self, mail: Mail, *, idempotency_key: str) -> str:
        """Hand `mail` to the provider; returns the provider's message id."""
        ...


class MockSender:
    def __init__(self) -> None:
        self.sent: list[tuple[str, Mail]] = []

    async def send(self, mail: Mail, *, idempotency_key: str) -> str:
        provider_ref = f"mock-{idempotency_key}"
        self.sent.append((idempotency_key, mail))
        log.info("[email:mock]", delivery_id=idempotency_key, provider_ref=provider_ref)
        return provider_ref


def urllib_post(url: str, headers: dict[str, str], body: bytes) -> tuple[int, bytes]:
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=RESEND_TIMEOUT_S) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


class ResendSender:
    def __init__(self, api_key: str, transport: Transport | None = None) -> None:
        if not api_key:
            raise ValueError("Resend needs an API key")
        self._api_key = api_key
        self._transport = transport or urllib_post

    async def send(self, mail: Mail, *, idempotency_key: str) -> str:
        body = json.dumps(
            {
                "from": mail.sender,
                "to": [mail.to],
                "subject": mail.subject,
                "text": mail.text,
                "html": mail.html,
            }
        ).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Idempotency-Key": idempotency_key,
            "User-Agent": "olspillet-mail",
        }
        try:
            status, answer = await asyncio.to_thread(self._transport, RESEND_URL, headers, body)
        except OSError as exc:  # network failure: no answer from the provider
            raise SendRefused("provider_unreachable") from exc
        if not 200 <= status < 300:
            raise SendRefused(f"provider_status_{status}")
        try:
            provider_id = json.loads(answer)["id"]
        except (ValueError, KeyError, TypeError) as exc:
            raise SendRefused("provider_answer_unreadable") from exc
        if not isinstance(provider_id, str) or not provider_id:
            raise SendRefused("provider_answer_unreadable")
        return provider_id


MOCK = MockSender()
"""The one mock per process, so tests can read what it got."""


def get_sender(settings: Settings | None = None) -> Sender:
    settings = settings or get_settings()
    if settings.resend_api_key:
        return ResendSender(settings.resend_api_key)
    if settings.app_env == "production":
        raise SendRefused("no_provider_key")
    return MOCK
