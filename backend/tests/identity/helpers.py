import httpx
from fastapi import FastAPI

from app.main import create_app
from app.platform.config import get_settings

CSRF = {"X-Requested-With": "olspillet"}

_apps: dict[str, FastAPI] = {}
"""One app per `APP_ENV`, the only setting `create_app` reads. FastAPI prepares each route on
its first request to an app, so a new app per client would prepare every route again."""


def app() -> FastAPI:
    env = get_settings().app_env
    if env not in _apps:
        _apps[env] = create_app()
    return _apps[env]


def client(ip: str = "203.0.113.7") -> httpx.AsyncClient:
    """The api over ASGI. https, so the client's cookie jar keeps and sends the Secure cookie."""
    transport = httpx.ASGITransport(app=app(), client=(ip, 50000))
    return httpx.AsyncClient(transport=transport, base_url="https://t")


async def login(c: httpx.AsyncClient, email: str, password: str) -> httpx.Response:
    body = {"email": email, "password": password}
    return await c.post("/api/auth/login", json=body, headers=CSRF)
