import httpx

from app.main import create_app


def client() -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app()), base_url="http://t")


async def test_health_ok_when_database_reachable(test_database):
    async with client() as c:
        response = await c.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_health_503_when_database_unreachable(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://nobody:secretpw@127.0.0.1:1/none")
    async with client() as c:
        response = await c.get("/api/health")
    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "db_unavailable"
    assert isinstance(body["error"]["message"], str)
    assert body["error"]["fields"] == {}
    assert "secretpw" not in response.text


async def test_routes_live_under_api_prefix(test_database):
    async with client() as c:
        assert (await c.get("/health")).status_code == 404
