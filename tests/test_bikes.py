"""Bikes API: list (incl. status filter), get, create, patch, delete."""

from fixtures import (
    client,
    image_bytes,
    seeded_client,
    tmp_db_path,
    uploads_dir,
)

SEEDED_NAMES = {"S-Works Tarmac SL8", "Surly Steamroller"}


async def test_list_empty(client):
    r = await client.get("/api/bikes")
    assert r.status_code == 200
    assert r.json() == []


async def test_list_seeded(seeded_client):
    r = await seeded_client.get("/api/bikes")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2
    assert {b["name"] for b in data} == SEEDED_NAMES

    sl8 = next(b for b in data if b["id"] == 1)
    assert {p["label"] for p in sl8["pills"]} == {"Carbon Frame", "Disc Brakes"}
    assert sl8["primary_image"] == "carbon-race-bike.jpg"
    assert sl8["primary_thumb"] == "carbon-race-bike.thumb.jpg"


async def test_list_status_filter_active(seeded_client):
    r = await seeded_client.get("/api/bikes", params={"status": "active"})
    data = r.json()
    assert [b["name"] for b in data] == ["S-Works Tarmac SL8"]


async def test_list_status_filter_former(seeded_client):
    r = await seeded_client.get("/api/bikes", params={"status": "former"})
    data = r.json()
    assert [b["name"] for b in data] == ["Surly Steamroller"]


async def test_list_invalid_status_falls_back(seeded_client):
    r = await seeded_client.get("/api/bikes", params={"status": "bogus"})
    assert r.status_code == 200
    assert len(r.json()) == 2


async def test_get_bike(seeded_client):
    r = await seeded_client.get("/api/bikes/1")
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "S-Works Tarmac SL8"
    assert len(data["images"]) == 1
    img = data["images"][0]
    assert img["filename"] == "carbon-race-bike.jpg"
    assert img["url"] == "/api/images/1/carbon-race-bike.jpg"
    assert img["thumb_url"] == "/api/images/1/carbon-race-bike.thumb.jpg"


async def test_get_bike_404(client):
    r = await client.get("/api/bikes/999")
    assert r.status_code == 404
    assert r.json()["detail"] == "Bike not found"


async def test_create_bike(client):
    r = await client.post("/api/bikes", json={"name": "New Steed"})
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "New Steed"
    assert data["description"] == ""
    assert data["status"] == "active"
    assert data["pills"] == []


async def test_create_bike_missing_name(client):
    r = await client.post("/api/bikes", json={})
    assert r.status_code == 422


async def test_patch_bike_partial(seeded_client):
    r = await seeded_client.patch(
        "/api/bikes/1", json={"description": "Updated description"}
    )
    assert r.status_code == 200
    data = r.json()
    assert data["description"] == "Updated description"
    assert data["name"] == "S-Works Tarmac SL8"  # untouched fields preserved


async def test_patch_bike_404(client):
    r = await client.patch("/api/bikes/999", json={"name": "x"})
    assert r.status_code == 404


async def test_patch_bike_empty_body(seeded_client):
    r = await seeded_client.patch("/api/bikes/1", json={})
    assert r.status_code == 200
    assert r.json()["name"] == "S-Works Tarmac SL8"


async def test_delete_bike(seeded_client):
    r = await seeded_client.delete("/api/bikes/1")
    assert r.status_code == 204
    assert (await seeded_client.get("/api/bikes/1")).status_code == 404


async def test_delete_bike_404(client):
    r = await client.delete("/api/bikes/999")
    assert r.status_code == 404
