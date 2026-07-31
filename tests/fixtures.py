"""Shared fixtures: tmp DB + tmp uploads + a seeded ASGI client.

Test modules import the fixtures they need by name (`from fixtures import
client, ...`) — no conftest.py. Imported names register as module-level
fixtures, so every module imports the full set (dependencies of `client`
must be registered in the same scope). ASGITransport never runs the app
lifespan, so `client` drives it by hand (async with lifespan(app)). All
fixtures patch module-level state that routes read at call time; the real
data/ and uploads/ dirs are never touched.
"""

import httpx
import pytest

import app.db as db_module
import app.routes.bikes as bikes_mod
import app.routes.images as images_mod
import app.routes.serve_images as serve_mod
from app.image_store import LocalImageStore
from app.seed import run_seed


@pytest.fixture
def tmp_db_path(tmp_path, monkeypatch):
    d = tmp_path / "data"
    d.mkdir()
    # get_db() reads these module globals at call time (db.py:60-62).
    monkeypatch.setattr(db_module, "DATA_DIR", d)
    monkeypatch.setattr(db_module, "DB_PATH", d / "bike_view.db")
    return d / "bike_view.db"


@pytest.fixture
def uploads_dir(tmp_path, monkeypatch):
    # Routes imported the image_store singleton BY NAME (bikes.py:5,
    # images.py:9) and serve_images bound UPLOADS_DIR at import (serve_images.py:4)
    # — patch the module attributes they actually reference at call time.
    store = LocalImageStore(tmp_path / "uploads")
    monkeypatch.setattr(bikes_mod, "image_store", store)
    monkeypatch.setattr(images_mod, "image_store", store)
    monkeypatch.setattr(serve_mod, "UPLOADS_DIR", store.base_dir)
    return store.base_dir


@pytest.fixture
async def client(tmp_db_path, uploads_dir):
    from app.main import app, lifespan

    transport = httpx.ASGITransport(app=app)
    async with lifespan(app):
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            yield c


@pytest.fixture
async def seeded_client(client):
    from app.main import app

    await run_seed(app.state.db)  # idempotent: INSERT OR IGNORE, fixed ids
    return client


@pytest.fixture
def image_bytes():
    from io import BytesIO

    from PIL import Image

    buf = BytesIO()
    Image.new("RGB", (64, 64), (180, 40, 40)).save(buf, "JPEG")
    return buf.getvalue()
