"""The signature of the mail provider's webhook (Story 4.6, AD-11, NFR-10).

Resend signs its webhooks the Svix way: the headers `svix-id`, `svix-timestamp` (Unix seconds)
and `svix-signature`, a space-separated list of `v1,<base64>`, each an HMAC-SHA256 of
`{id}.{timestamp}.{raw body}` under the key the secret `whsec_<base64>` holds. A timestamp more
than `TOLERANCE` from the api's clock is refused, so a captured request cannot be replayed later.
Standard library only.
"""

import base64
import hashlib
import hmac
from collections.abc import Mapping
from datetime import datetime, timedelta

from app.platform.config import webhook_key

ID = "svix-id"
TIMESTAMP = "svix-timestamp"
SIGNATURE = "svix-signature"
TOLERANCE = timedelta(minutes=5)
MAX_ID_LENGTH = 200


class SignatureInvalid(Exception):
    """The request is not signed with the secret, or not now. Nothing about it is stored."""


def sign(secret: str, event_id: str, timestamp: int, body: bytes) -> str:
    """The `svix-signature` value for `body` (the dev bounce route and the tests sign with it)."""
    key = webhook_key(secret)
    if key is None:
        raise ValueError("not a webhook secret")
    signed = f"{event_id}.{timestamp}.".encode() + body
    digest = hmac.new(key, signed, hashlib.sha256).digest()
    return "v1," + base64.b64encode(digest).decode("ascii")


def verify(secret: str, headers: Mapping[str, str], body: bytes, now: datetime) -> str:
    """The event id of a request signed with `secret` within `TOLERANCE` of `now`; raises
    `SignatureInvalid` otherwise. `headers` are looked up lower-case."""
    event_id = headers.get(ID, "")
    stamp = headers.get(TIMESTAMP, "")
    given = headers.get(SIGNATURE, "")
    if not event_id or len(event_id) > MAX_ID_LENGTH or not event_id.isprintable():
        raise SignatureInvalid
    if not stamp.isascii() or not stamp.isdigit() or len(stamp) > 12:
        raise SignatureInvalid
    sent = int(stamp)
    if abs(now.timestamp() - sent) > TOLERANCE.total_seconds():
        raise SignatureInvalid
    if webhook_key(secret) is None:
        raise SignatureInvalid
    expected = sign(secret, event_id, sent, body)
    for candidate in given.split():
        if hmac.compare_digest(candidate.encode("ascii", "replace"), expected.encode("ascii")):
            return event_id
    raise SignatureInvalid
