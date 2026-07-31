"""Pills API: list, create (incl. duplicate/blank), delete (incl. cascade)."""

from fixtures import (
    client,
    image_bytes,
    seeded_client,
    tmp_db_path,
    uploads_dir,
)


async def test_list(seeded_client):
    r = await seeded_client.get("/api/pills")
    assert r.status_code == 200
    labels = [p["label"] for p in r.json()]
    assert labels == [
        "Carbon Frame",
        "Disc Brakes",
        "Gravel Bike",
        "Singlespeed",
        "Titanium",
    ]  # ordered by label


async def test_create(client):
    r = await client.post("/api/pills", json={"label": "Steel", "color": "#111827"})
    assert r.status_code == 201
    data = r.json()
    assert data["label"] == "Steel"
    assert data["color"] == "#111827"


async def test_create_duplicate(seeded_client):
    r = await seeded_client.post("/api/pills", json={"label": "Singlespeed"})
    assert r.status_code == 409
    assert "already exists" in r.json()["detail"]


async def test_create_blank_label(client):
    r = await client.post("/api/pills", json={"label": "   "})
    assert r.status_code == 422


async def test_delete(seeded_client):
    r = await seeded_client.delete("/api/pills/1")
    assert r.status_code == 204
    labels = [p["label"] for p in (await seeded_client.get("/api/pills")).json()]
    assert len(labels) == 4
    assert "Carbon Frame" not in labels


async def test_delete_cascades_attachment(seeded_client):
    # Bike 1 has Carbon Frame + Disc Brakes; deleting the pill must
    # detach it from the bike (FK cascade) — no dangling join rows.
    r = await seeded_client.delete("/api/pills/1")  # Carbon Frame
    assert r.status_code == 204
    bike = (await seeded_client.get("/api/bikes/1")).json()
    assert [p["label"] for p in bike["pills"]] == ["Disc Brakes"]


async def test_delete_404(client):
    r = await client.delete("/api/pills/999")
    assert r.status_code == 404
