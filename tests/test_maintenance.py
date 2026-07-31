"""Maintenance API: list (date DESC), create, patch, delete."""

from fixtures import (
    client,
    image_bytes,
    seeded_client,
    tmp_db_path,
    uploads_dir,
)


async def test_list_seeded(seeded_client):
    r = await seeded_client.get("/api/bikes/1/maintenance")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2
    assert [rec["date"] for rec in data] == ["2025-01-03", "2024-06-15"]  # DESC
    assert data[0]["cost"] == 85.0


async def test_list_bike_404(client):
    r = await client.get("/api/bikes/999/maintenance")
    assert r.status_code == 404


async def test_create(seeded_client):
    r = await seeded_client.post(
        "/api/bikes/1/maintenance",
        json={"date": "2025-05-01", "description": "Full tune-up", "cost": 50},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["date"] == "2025-05-01"
    assert data["cost"] == 50.0


async def test_create_bike_404(client):
    r = await client.post(
        "/api/bikes/999/maintenance",
        json={"date": "2025-05-01", "description": "x"},
    )
    assert r.status_code == 404


async def test_patch(seeded_client):
    r = await seeded_client.patch(
        "/api/bikes/1/maintenance/1", json={"description": "Rewaxed"}
    )
    assert r.status_code == 200
    data = r.json()
    assert data["description"] == "Rewaxed"
    assert data["date"] == "2024-06-15"  # untouched


async def test_patch_404(client):
    r = await client.patch(
        "/api/bikes/1/maintenance/999", json={"description": "x"}
    )
    assert r.status_code == 404


async def test_delete(seeded_client):
    r = await seeded_client.delete("/api/bikes/1/maintenance/1")
    assert r.status_code == 204
    remaining = (await seeded_client.get("/api/bikes/1/maintenance")).json()
    assert len(remaining) == 1


async def test_delete_404(client):
    r = await client.delete("/api/bikes/1/maintenance/999")
    assert r.status_code == 404
