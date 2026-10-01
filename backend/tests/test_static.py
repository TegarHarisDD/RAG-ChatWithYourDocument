import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest_asyncio.fixture
async def spa_client(settings, database, tmp_path):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text(
        "<!doctype html><div id=\"root\">PORTO_APP</div>", encoding="utf-8"
    )
    (dist / "assets" / "app.js").write_text("console.log('cwd')", encoding="utf-8")

    spa_settings = settings.model_copy(update={"frontend_dist": str(dist)})
    app = create_app(settings=spa_settings, db=database)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="https://testserver") as client:
        yield client


async def test_root_serves_the_frontend(spa_client):
    response = await spa_client.get("/")
    assert response.status_code == 200
    assert "PORTO_APP" in response.text


async def test_unknown_non_api_path_serves_the_frontend(spa_client):
    response = await spa_client.get("/sessions/abc/does-not-exist")
    assert response.status_code == 200
    assert "PORTO_APP" in response.text


async def test_unknown_api_path_returns_json_404(spa_client):
    response = await spa_client.get("/api/does-not-exist")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")


async def test_built_asset_is_served(spa_client):
    response = await spa_client.get("/assets/app.js")
    assert response.status_code == 200
    assert "cwd" in response.text
