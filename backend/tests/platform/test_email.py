"""Story 3.5: `platform/email` renders Norwegian mails headed «ØL-spillet» from Jinja2 templates
and sends them through Resend or the deterministic `[email:mock]` sender (AD-17, AD-19)."""

import io
import json
import logging

import pytest

from app.platform.config import Settings
from app.platform.email import (
    Mail,
    MockSender,
    Recipient,
    ResendSender,
    Section,
    SendRefused,
    get_sender,
    render,
    senders,
)
from app.platform.logging import configure_logging


@pytest.fixture
def log_stream():
    stream = io.StringIO()
    configure_logging("info", stream=stream)
    yield stream
    logging.getLogger().handlers[:] = []


def test_an_immediate_mail_is_headed_from_email_from_with_links_on_the_public_base_url(
    monkeypatch,
):
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://olspillet.example/")
    monkeypatch.setenv("EMAIL_FROM", "ØL-spillet <noreply@olspillet.example>")
    mail = render(
        Recipient("kari@example.no", "Kari <b>"), [Section("test_immediate")], digest=False
    )
    assert mail.to == "kari@example.no"
    assert mail.sender == "ØL-spillet <noreply@olspillet.example>"
    assert mail.subject == "Testmelding fra ØL-spillet"
    assert mail.text.startswith("ØL-spillet\n\nHei Kari <b>,")
    assert "https://olspillet.example/" in mail.text
    assert 'href="https://olspillet.example/"' in mail.html
    assert "Kari &lt;b&gt;" in mail.html  # names are escaped in HTML
    assert '<html lang="nb">' in mail.html
    for part in (mail.subject, mail.text):
        assert "!" not in part


def test_a_digest_carries_one_part_per_notice_under_its_own_subject():
    sections = [Section("test_digest"), Section("test_digest"), Section("test_digest")]
    mail = render(Recipient("kari@example.no"), sections, digest=True)
    assert mail.subject == "Nytt fra ØL-spillet"
    assert mail.text.count("Dette er et testvarsel.") == 3
    assert mail.html.count("Dette er et testvarsel.") == 3
    assert "Hei," in mail.text  # no name


def test_render_refuses_no_part_or_several_parts_in_an_immediate_mail():
    with pytest.raises(ValueError, match="at least one"):
        render(Recipient("a@example.no"), [], digest=True)
    with pytest.raises(ValueError, match="exactly one"):
        render(Recipient("a@example.no"), [Section("test_immediate")] * 2, digest=False)


MAIL = Mail(
    to="kari@example.no", sender="ØL-spillet <x@y>", subject="Emne", text="Tekst", html="<p>x</p>"
)


async def test_the_mock_logs_ids_only_and_answers_the_same_id_for_the_same_key(log_stream):
    mock = MockSender()
    assert await mock.send(MAIL, idempotency_key="d1") == "mock-d1"
    assert await mock.send(MAIL, idempotency_key="d1") == "mock-d1"
    [line, _] = [json.loads(x) for x in log_stream.getvalue().splitlines()]
    assert line["event"] == "[email:mock]"
    assert line["delivery_id"] == "d1" and line["provider_ref"] == "mock-d1"
    assert "kari@example.no" not in log_stream.getvalue()
    assert [key for key, _ in mock.sent] == ["d1", "d1"]


async def test_resend_posts_the_mail_with_the_key_and_an_idempotency_key():
    seen = {}

    def transport(url, headers, body):
        seen.update(url=url, headers=headers, body=json.loads(body))
        return 200, b'{"id": "re_123"}'

    sender = ResendSender("re_test_key", transport=transport)
    assert await sender.send(MAIL, idempotency_key="d1") == "re_123"
    assert seen["url"] == senders.RESEND_URL
    assert seen["headers"]["Authorization"] == "Bearer re_test_key"
    assert seen["headers"]["Idempotency-Key"] == "d1"
    assert seen["body"] == {
        "from": "ØL-spillet <x@y>",
        "to": ["kari@example.no"],
        "subject": "Emne",
        "text": "Tekst",
        "html": "<p>x</p>",
    }


@pytest.mark.parametrize(
    ("answer", "code"),
    [
        ((422, b'{"message": "kari@example.no is invalid"}'), "provider_status_422"),
        ((200, b"not json"), "provider_answer_unreadable"),
        ((200, b'{"id": null}'), "provider_answer_unreadable"),
        (OSError("down"), "provider_unreachable"),
    ],
)
async def test_resend_refusals_carry_a_code_and_never_the_address(answer, code):
    def transport(url, headers, body):
        if isinstance(answer, Exception):
            raise answer
        return answer

    with pytest.raises(SendRefused) as info:
        await ResendSender("k", transport=transport).send(MAIL, idempotency_key="d1")
    assert str(info.value) == code


def test_the_sender_is_resend_with_a_key_the_mock_without_and_refused_in_production():
    assert isinstance(get_sender(Settings(resend_api_key="k")), ResendSender)
    assert get_sender(Settings(app_env="local")) is senders.MOCK
    assert get_sender(Settings(app_env="test")) is senders.MOCK
    with pytest.raises(SendRefused, match="no_provider_key"):
        get_sender(Settings(app_env="production", database_url="postgresql://x/y"))
    with pytest.raises(ValueError):
        ResendSender("")
