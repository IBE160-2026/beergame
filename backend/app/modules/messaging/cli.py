"""Send a test notice through the whole mail pipeline (Story 3.5), outside production only.

    python -m app.modules.messaging.cli send-test --user <id> --kind test_immediate

`test_immediate` leaves at once through the claim job: `worker-batch` logs one `[email:mock]`
line within seconds. `test_digest` waits for the next sweep inside 07:00–22:00 Europe/Oslo, and
for the next day when the User already got today's digest. Each mail gets a `mail_deliveries`
row. The command prints the kind and the User id only.
"""

import argparse
import asyncio
import sys
import uuid
from collections.abc import Sequence

from app.modules.identity import service as identity
from app.modules.messaging import delivery
from app.platform import notify
from app.platform.config import get_settings
from app.platform.db import dispose, get_sessionmaker


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.modules.messaging.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    send_test = commands.add_parser("send-test", help="enqueue one test notice")
    send_test.add_argument("--user", required=True, type=uuid.UUID, help="the User's id")
    send_test.add_argument(
        "--kind", required=True, choices=sorted(delivery.TEST_KINDS), help="a dummy kind"
    )
    return parser


async def send_test(user_id: uuid.UUID, kind: str) -> uuid.UUID | None:
    """Enqueue one notice of the dummy `kind` to `user_id`; None when there is no active User."""
    async with get_sessionmaker().begin() as session:
        if await identity.mail_recipient(session, user_id) is None:
            return None
        await notify.enqueue(session, user_id, kind, f"send-test:{uuid.uuid7()}")
    return user_id


async def _run(user_id: uuid.UUID, kind: str) -> uuid.UUID | None:
    try:
        return await send_test(user_id, kind)
    finally:
        await dispose()


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if get_settings().app_env == "production":
        print("send-test finnes ikke i production.", file=sys.stderr)
        return 2
    factory = asyncio.SelectorEventLoop if sys.platform == "win32" else asyncio.new_event_loop
    found = asyncio.run(_run(args.user, args.kind), loop_factory=factory)
    if found is None:
        print("Ingen aktiv bruker med den id-en.", file=sys.stderr)
        return 1
    print(f"Testvarsel {args.kind} lagt i kø for bruker {args.user}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
