from httpx import ASGITransport, AsyncClient

from app.main import create_app


class BrokenDB:
    """A database whose every operation fails, to exercise the health report."""

    db = None

    async def ping(self):
        raise RuntimeError("database down")

    async def ensure_indexes(self):
        raise RuntimeError("database down")

    def close(self):
        pass


async def test_health_ok_when_database_responds(client):
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


async def test_health_not_ok_when_database_is_down(settings):
    app = create_app(settings=settings, db=BrokenDB())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="https://testserver") as client:
        response = await client.get("/api/health")
    assert response.status_code != 200
    assert response.json()["status"] != "ok"


async def test_health_is_public(client):
    response = await client.get("/api/health")
    assert response.status_code == 200
