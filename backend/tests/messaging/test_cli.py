"""Story 3.5: `python -m app.modules.messaging.cli send-test --user <id> --kind <kind>` sends a
dummy notice through the whole pipeline, outside production only."""

import uuid

import pytest

from app.modules.messaging import cli
from app.modules.ops import sweep
from tests.messaging.helpers import deliveries, drain, mails, oslo, user


async def test_send_test_immediate_gives_one_mock_mail_with_its_delivery_row(mail_db):
    user_id = await user()
    assert await cli.send_test(user_id, "test_immediate") == user_id
    await drain()
    assert [m.subject for m in mails()] == ["Testmelding fra ØL-spillet"]
    assert deliveries() == [("immediate", 1, True, None, 1)]


async def test_send_test_digest_leaves_at_the_next_sweep_inside_allowed_hours(mail_db):
    user_id = await user()
    await cli.send_test(user_id, "test_digest")
    await drain()
    assert mails() == []
    await sweep.run(oslo(12, 9))
    await drain(oslo(12, 9))
    assert [m.subject for m in mails()] == ["Nytt fra ØL-spillet"]
    assert deliveries() == [("digest", 1, True, None, 1)]


async def test_send_test_needs_an_active_user(mail_db):
    assert await cli.send_test(uuid.uuid7(), "test_immediate") is None
    assert await cli.send_test(await user(is_active=False), "test_immediate") is None


def test_send_test_does_not_exist_in_production(monkeypatch, capsys):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@db:5432/prod")
    assert cli.main(["send-test", "--user", str(uuid.uuid7()), "--kind", "test_immediate"]) == 2
    assert "production" in capsys.readouterr().err


@pytest.mark.parametrize(
    "argv",
    [
        ["send-test", "--user", "x", "--kind", "test_immediate"],
        ["send-test", "--user", str(uuid.uuid7()), "--kind", "invitation"],
        [],
    ],
)
def test_send_test_refuses_a_bad_user_id_or_a_real_kind(argv):
    with pytest.raises(SystemExit) as info:
        cli.main(argv)
    assert info.value.code == 2
