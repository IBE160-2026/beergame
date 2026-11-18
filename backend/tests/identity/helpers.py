import httpx

from app.main import create_app

CSRF = {"X-Requested-With": "olspillet"}


def client(ip: str = "203.0.113.7") -> httpx.AsyncClient:
    """The api over ASGI. https, so the client's cookie jar keeps and sends the Secure cookie."""
    transport = httpx.ASGITransport(app=create_app(), client=(ip, 50000))
    return httpx.AsyncClient(transport=transport, base_url="https://t")


async def login(c: httpx.AsyncClient, email: str, password: str) -> httpx.Response:
    body = {"email": email, "password": password}
    return await c.post("/api/auth/login", json=body, headers=CSRF)
