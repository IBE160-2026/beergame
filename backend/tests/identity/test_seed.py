"""The local demo accounts (AD-17): only with `APP_ENV=local`, only on an empty `users` table."""

import pytest
import structlog
import structlog.testing
from sqlalchemy import func, select

from app.modules.identity import seed, service
from app.modules.identity.models import user_roles, users
from app.platform.db import get_sessionmaker
from tests.identity.helpers import client, login


async def _counts() -> tuple[int, int]:
    async with get_sessionmaker().begin() as s:
        n_users = (await s.execute(select(func.count()).select_from(users))).scalar_one()
        n_roles = (await s.execute(select(func.count()).select_from(user_roles))).scalar_one()
    return n_users, n_roles


async def test_local_seeds_one_admin_and_one_lecturer_once(identity_db, monkeypatch):
    monkeypatch.setenv("APP_ENV", "local")
    assert await seed.ensure_demo_users() == 2
    assert await seed.ensure_demo_users() == 0
    assert await _counts() == (2, 2)
    async with client() as c:
        for demo in seed.DEMO_USERS:
            response = await login(c, demo.email, seed.DEMO_PASSWORD)
            assert response.status_code == 200
            assert response.json()["user"]["roles"] == [r.value for r in demo.roles]


@pytest.mark.parametrize("env", ["test", "ci"])
async def test_no_seed_outside_local(identity_db, monkeypatch, env):
    monkeypatch.setenv("APP_ENV", env)
    assert await seed.ensure_demo_users() == 0
    assert await _counts() == (0, 0)


async def test_production_never_seeds(identity_db, monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", identity_db)
    assert await seed.ensure_demo_users() == 0
    assert await _counts() == (0, 0)


async def test_no_seed_when_a_user_exists(identity_db, monkeypatch):
    await service.create_user(email="kari@example.com", name="Kari", password="x" * 12)
    monkeypatch.setenv("APP_ENV", "local")
    assert await seed.ensure_demo_users() == 0
    assert await _counts() == (1, 0)


async def test_a_database_error_at_start_is_logged_not_raised(monkeypatch, unreachable_database):
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("DATABASE_URL", unreachable_database)
    with structlog.testing.capture_logs() as logs:
        await seed.ensure_demo_users_logged()
    assert [entry["event"] for entry in logs] == ["demo_users_failed"]
    assert logs[0]["error_code"] == "db_error"
