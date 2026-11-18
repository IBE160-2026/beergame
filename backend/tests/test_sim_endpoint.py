"""Story 2.7: `python -m app.sim endpoint` (the hand check of a real endpoint) and the key
check of `python -m app.sim run` (AD-17), against a fake HTTP transport: no test reaches a
real endpoint."""

from decimal import Decimal

import httpx2

from app.ai import adapters, budget, config
from app.platform.config import get_settings
from tests.ai.helpers import mock_config, stored_config
from tests.ai.test_adapters import KEY_ENV, MODEL, FakeEndpoint, real_config
from tests.test_sim_llm import batch, run, setup


async def _real_config(**changes) -> str:
    row = await config.add(config.parse(real_config(**changes)))
    await budget.set_budget(
        budget.BudgetScope.evaluation(row.id), limit=Decimal(1), reserve=Decimal(0)
    )
    return str(row.id)


def report(out: str) -> list[str]:
    """The report lines, without the log lines that tests let through to stdout."""
    return [line for line in out.splitlines() if not line[:4].isdigit()]


class Unlisted(FakeEndpoint):
    def handle(self, request):
        if request.url.path.endswith("/models"):
            self.requests.append(request)
            return httpx2.Response(401, json={"error": {"message": "no auth"}})
        return super().handle(request)


def test_the_endpoint_probe_reports_model_orders_burst_and_cost(
    capsys, games_db, ai_db, monkeypatch
):
    monkeypatch.setenv(KEY_ENV, "test-key-not-real")
    config_id = setup(_real_config())
    fake = FakeEndpoint((429, {"error": {"message": "busy"}}, {"retry-after": "1"}))
    with adapters.use_transport(httpx2.MockTransport(fake.handle)):
        code, out, err = run(capsys, "endpoint", "--config", config_id, "--burst", "2")
    assert code == 0, err
    assert "playing one Rule-based Game first" in err
    lines = report(out)
    assert lines[0].startswith(f"config {config_id} ")
    assert '"allow_fallbacks": false' in lines[2] and '"zdr": true' in lines[2]
    assert "model_listed yes (1 models)" in lines
    orders = [line for line in lines if line.startswith("order ")]
    assert len(orders) == 3 and all(" ok order=7 attempts=1 " in line for line in orders)
    assert all(f"served={MODEL} by=Nebius" in line for line in orders)
    assert any(line.startswith("burst 2 ok=2 rate_limited=0 ") for line in lines)
    assert f"served_model {MODEL}" in lines and "served_by Nebius" in lines
    assert any(line.startswith("cost_usd total=0.0") for line in lines)
    assert lines[-1] == "endpoint ok"
    # The first Order met a 429: it waited and got its answer with one logged attempt.
    assert len([r for r in fake.requests if r.method == "POST"]) == 6


def test_the_probe_fails_when_the_model_list_cannot_be_read(capsys, games_db, ai_db, monkeypatch):
    monkeypatch.setenv(KEY_ENV, "test-key-not-real")
    config_id = setup(_real_config())
    fake = Unlisted()
    with adapters.use_transport(httpx2.MockTransport(fake.handle)):
        code, out, _ = run(capsys, "endpoint", "--config", config_id, "--orders", "1")
    assert code == 1
    assert report(out)[-1] == "endpoint failed: model list not read"


def test_the_probe_needs_a_real_endpoint(capsys, games_db, ai_db, monkeypatch):
    monkeypatch.delenv(KEY_ENV, raising=False)
    real_id = setup(_real_config())
    code, out, err = run(capsys, "endpoint", "--config", real_id)
    assert (code, out) == (2, "")
    assert f"error endpoint_unavailable: mock: {KEY_ENV} is not set" in err
    mock_id = setup(stored_config())
    code, _, err = run(capsys, "endpoint", "--config", mock_id)
    assert code == 2 and "the config's provider is the mock" in err
    missing = "00000000-0000-7000-8000-000000000009"
    code, _, err = run(capsys, "endpoint", "--config", missing)
    assert code == 2 and "error config_not_found" in err
    code, _, err = run(capsys, "endpoint", "--config", "not-an-id")
    assert code == 2 and "error config_not_found" in err


def test_run_refuses_a_missing_key_outside_the_mock_environments(
    capsys, tmp_path, games_db, ai_db, monkeypatch
):
    monkeypatch.delenv(KEY_ENV, raising=False)
    config_id = setup(_real_config(prompts={"player_order": 1}))
    path = batch(tmp_path, config_id)
    code, out, err = run(capsys, "run", path)  # APP_ENV=test: the mock answers
    assert code == 0, err
    assert f"note: mock provider in use for config {config_id} ({KEY_ENV} is not set)" in err
    monkeypatch.setenv("APP_ENV", "production")
    get_settings.cache_clear()
    code, out, err = run(capsys, "run", path)
    assert (code, out) == (2, "")
    assert err.strip() == f"error key_missing: {KEY_ENV} is not set"


def test_a_mock_config_in_production_is_refused_by_run(
    capsys, tmp_path, games_db, ai_db, monkeypatch
):
    config_id = setup(stored_config())
    assert mock_config()["provider"] == "mock"
    monkeypatch.setenv("APP_ENV", "production")
    get_settings.cache_clear()
    code, _, err = run(capsys, "run", batch(tmp_path, config_id))
    assert code == 2
    assert err.strip() == (
        "error model_unavailable: the mock provider is never used with APP_ENV=production"
    )


def test_the_served_model_must_be_the_pinned_one():
    from app.ai.endpoint import served_matches

    assert served_matches(MODEL, MODEL)
    assert served_matches(MODEL, "deepseek/deepseek-v4.1-flash-20261017")  # dated snapshot
    assert not served_matches(MODEL, "deepseek/deepseek-v4.1-flash-11017")
    assert not served_matches(MODEL, "deepseek/deepseek-v4.1-flash-20260910")
    assert not served_matches(MODEL, "deepseek/deepseek-v4-pro-1017")
    assert not served_matches(MODEL, None)
