"""The local demo accounts (AD-17): only with `APP_ENV=local`, only for e-mails not yet taken."""

import pytest
import structlog
import structlog.testing
from sqlalchemy import func, select

from app.modules.identity import seed, service
from app.modules.identity.models import user_roles, users
from app.platform.db import get_sessionmaker
from tests.conftest import enter_production
from tests.identity.helpers import client, login


async def _counts() -> tuple[int, int]:
    async with get_sessionmaker().begin() as s:
        n_users = (await s.execute(select(func.count()).select_from(users))).scalar_one()
        n_roles = (await s.execute(select(func.count()).select_from(user_roles))).scalar_one()
    return n_users, n_roles


async def test_local_seeds_the_four_demo_users_once(identity_db, monkeypatch):
    monkeypatch.setenv("APP_ENV", "local")
    assert await seed.ensure_demo_users() == 4
    assert await seed.ensure_demo_users() == 0
    # Admin, Lecturer, Admin and Lecturer, and one with no account role (Hjem).
    assert await _counts() == (4, 4)
    assert sorted(len(demo.roles) for demo in seed.DEMO_USERS) == [0, 1, 1, 2]
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
    enter_production(monkeypatch)
    monkeypatch.setenv("DATABASE_URL", identity_db)
    assert await seed.ensure_demo_users() == 0
    assert await _counts() == (0, 0)


async def test_only_missing_demo_users_are_added_and_existing_users_are_kept(
    identity_db, monkeypatch
):
    """A database seeded by Story 3.2 gets the two new demo Users; a User who already holds a
    demo e-mail is left as they are."""
    monkeypatch.setenv("APP_ENV", "local")  # before the first get_settings(), which caches
    await service.create_user(email="kari@example.com", name="Kari", password="x" * 12)
    await service.create_user(email="admin@example.com", name="Endret", password="x" * 12)
    assert await seed.ensure_demo_users() == 3
    assert await _counts() == (5, 3)  # the existing «admin@» keeps no role and its name
    async with client() as c:
        response = await login(c, "admin@example.com", seed.DEMO_PASSWORD)
        assert response.status_code == 401


async def test_a_database_error_at_start_is_logged_not_raised(monkeypatch, unreachable_database):
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("DATABASE_URL", unreachable_database)
    with structlog.testing.capture_logs() as logs:
        await seed.ensure_demo_users_logged()
    assert [entry["event"] for entry in logs] == ["demo_users_failed"]
    assert logs[0]["error_code"] == "db_error"
