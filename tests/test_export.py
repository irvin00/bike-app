"""Export API: full nested JSON dump of the database."""

from fixtures import (
    client,
    seeded_client,
    tmp_db_path,
    uploads_dir,
)


async def test_export_empty(client):
    r = await client.get("/api/export")
    assert r.status_code == 200
    data = r.json()
    assert data["bikes"] == []
    assert data["pills"] == []
    assert "exported_at" in data


async def test_export_seeded(seeded_client):
    r = await seeded_client.get("/api/export")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/json")
    disposition = r.headers["content-disposition"]
    assert "attachment" in disposition
    assert "bike_view.json" in disposition

    data = r.json()
    assert len(data["bikes"]) == 2
    assert len(data["pills"]) == 5

    sl8 = next(b for b in data["bikes"] if b["id"] == 1)
    assert sl8["name"] == "S-Works Tarmac SL8"
    assert {p["label"] for p in sl8["pills"]} == {"Carbon Frame", "Disc Brakes"}
    img = sl8["images"][0]
    assert img["url"] == "/api/images/1/carbon-race-bike.jpg"
    assert img["thumb_url"] == "/api/images/1/carbon-race-bike.thumb.jpg"

    records = sl8["maintenance_records"]
    assert len(records) == 2
    assert {r["cost"] for r in records} == {0, 85.0}
