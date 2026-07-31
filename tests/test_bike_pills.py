"""Bike-pill attachment API: PUT replaces the attachment set atomically."""

from fixtures import (
    client,
    image_bytes,
    seeded_client,
    tmp_db_path,
    uploads_dir,
)


async def test_set(seeded_client):
    r = await seeded_client.put("/api/bikes/1/pills", json={"pill_ids": [2, 3]})
    assert r.status_code == 200
    pills = r.json()
    assert {p["id"] for p in pills} == {2, 3}
    # Ordered by label: Singlespeed < Titanium
    assert [p["label"] for p in pills] == ["Singlespeed", "Titanium"]


async def test_set_replaces_existing(seeded_client):
    await seeded_client.put("/api/bikes/1/pills", json={"pill_ids": [2, 3]})
    r = await seeded_client.put("/api/bikes/1/pills", json={"pill_ids": [5]})
    assert r.status_code == 200
    assert [p["id"] for p in r.json()] == [5]


async def test_set_bike_404(client):
    r = await client.put("/api/bikes/999/pills", json={"pill_ids": [1]})
    assert r.status_code == 404
