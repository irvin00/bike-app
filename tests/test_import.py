"""POST /api/import: full-restore from a bike_view.json export.

Round-trip with the real export endpoint, replace/wipe semantics, and the
all-or-nothing validation contract (422 with a string detail — api.js
surfaces err.detail verbatim — and zero writes before validation passes).
"""

import json

from fixtures import client, seeded_client, tmp_db_path, uploads_dir


def make_pill(pill_id=1, label="Steel Frame", color="#b45309"):
    return {"id": pill_id, "label": label, "color": color}


def make_bike(bike_id=1, name="Test Bike", status="active", pills=None, images=None, records=None):
    return {
        "id": bike_id,
        "name": name,
        "status": status,
        "description": "",
        "full_story": "",
        "acquired_on": None,
        "retired_on": None,
        "created_at": "2026-01-01 00:00:00",
        "updated_at": "2026-01-01 00:00:00",
        "pills": pills or [],
        "images": images or [],
        "maintenance_records": records or [],
    }


def make_export(bikes=None, pills=None):
    return {"exported_at": "2026-08-06T00:00:00+00:00", "pills": pills or [], "bikes": bikes or []}


async def export_payload(client):
    r = await client.get("/api/export")
    assert r.status_code == 200
    return r.json()


async def post_import(client, payload):
    return await client.post(
        "/api/import",
        files={"file": ("bike_view.json", json.dumps(payload), "application/json")},
    )


def bike_essence(bike):
    """Bike dict minus ids/timestamps that legitimately change across a
    round-trip (image/maintenance rows are re-inserted with fresh ids)."""
    return {
        "name": bike["name"],
        "status": bike["status"],
        "description": bike["description"],
        "full_story": bike["full_story"],
        "acquired_on": bike["acquired_on"],
        "retired_on": bike["retired_on"],
        "pills": sorted(p["id"] for p in bike["pills"]),
        "images": sorted(i["filename"] for i in bike["images"]),
        "maintenance": sorted(
            (m["date"], m["description"], m["cost"]) for m in bike["maintenance_records"]
        ),
    }


async def test_import_round_trip(seeded_client):
    before = await export_payload(seeded_client)
    r = await post_import(seeded_client, before)
    assert r.status_code == 200
    assert r.json() == {"bikes": 2, "pills": 5, "images": 2, "maintenance": 4}

    after = await export_payload(seeded_client)
    assert after["pills"] == before["pills"]  # pill ids/labels/colors preserved
    assert [bike_essence(b) for b in after["bikes"]] == [
        bike_essence(b) for b in before["bikes"]
    ]


async def test_import_replaces_existing(seeded_client):
    r = await seeded_client.post("/api/bikes", json={"name": "Extra Bike"})
    assert r.status_code == 201

    payload = make_export(
        pills=[make_pill()],
        bikes=[make_bike(pills=[{"id": 1}])],
    )
    r = await post_import(seeded_client, payload)
    assert r.status_code == 200
    assert r.json() == {"bikes": 1, "pills": 1, "images": 0, "maintenance": 0}

    bikes = (await seeded_client.get("/api/bikes")).json()
    assert [b["name"] for b in bikes] == ["Test Bike"]


async def test_import_empty_wipes(seeded_client):
    r = await post_import(seeded_client, make_export())
    assert r.status_code == 200
    assert r.json() == {"bikes": 0, "pills": 0, "images": 0, "maintenance": 0}

    payload = await export_payload(seeded_client)
    assert payload["bikes"] == []
    assert payload["pills"] == []

    page = await seeded_client.get("/")
    assert "No bikes yet" in page.text


async def test_import_invalid_json(client):
    r = await client.post(
        "/api/import",
        files={"file": ("bike_view.json", b"not json", "application/json")},
    )
    assert r.status_code == 422
    assert isinstance(r.json()["detail"], str)


async def test_import_no_file(client):
    r = await client.post("/api/import", files={})
    assert r.status_code == 422
    assert isinstance(r.json()["detail"], str)


async def test_import_missing_keys(client):
    for payload in ({}, {"bikes": []}, {"pills": []}):
        r = await post_import(client, payload)
        assert r.status_code == 422, payload
        assert "Invalid export file" in r.json()["detail"]


async def test_import_wrong_types(client):
    bad_bikes = [
        "nope",  # bikes as a string
        {"id": 1, "name": 42, "pills": [], "images": [], "maintenance_records": []},
        make_bike(status="retired"),  # not in ('active', 'former')
    ]
    for bikes in bad_bikes:
        r = await post_import(client, make_export(bikes=bikes))
        assert r.status_code == 422
        assert "Invalid export file" in r.json()["detail"]


async def test_import_unknown_pill_ref(client):
    payload = make_export(bikes=[make_bike(pills=[{"id": 99}])])
    r = await post_import(client, payload)
    assert r.status_code == 422
    assert "unknown pill id 99" in r.json()["detail"]


async def test_import_duplicates(client):
    cases = [
        # duplicate bike ids
        make_export(bikes=[make_bike(), make_bike()]),
        # duplicate pill ids
        make_export(pills=[make_pill(1), make_pill(1, label="Other")]),
        # duplicate pill labels
        make_export(pills=[make_pill(1), make_pill(2, label="Steel Frame")]),
    ]
    for payload in cases:
        r = await post_import(client, payload)
        assert r.status_code == 422, payload


async def test_import_duplicate_is_primary(client):
    payload = make_export(
        bikes=[
            make_bike(
                images=[
                    {"filename": "a.jpg", "is_primary": True},
                    {"filename": "b.jpg", "is_primary": True},
                ]
            )
        ]
    )
    r = await post_import(client, payload)
    assert r.status_code == 422
    assert "more than one primary" in r.json()["detail"]


async def test_import_unsafe_filename(client):
    for filename in ("../evil.jpg", "a/b.jpg", ""):
        payload = make_export(
            bikes=[make_bike(images=[{"filename": filename}])]
        )
        r = await post_import(client, payload)
        assert r.status_code == 422, filename
        assert "unsafe image filename" in r.json()["detail"]


async def test_import_mismatched_nested_bike_id(client):
    cases = [
        make_bike(images=[{"filename": "a.jpg", "bike_id": 2}]),
        make_bike(records=[{"date": "2026-01-01", "description": "x", "bike_id": 2}]),
    ]
    for bike in cases:
        r = await post_import(client, make_export(bikes=[bike]))
        assert r.status_code == 422
        assert "does not match" in r.json()["detail"]


async def test_import_all_or_nothing(seeded_client):
    """A file that fails a cross-check on the second bike writes nothing."""
    payload = make_export(
        bikes=[
            make_bike(1, name="First"),
            make_bike(2, name="Second", pills=[{"id": 999}]),  # unknown pill ref
        ]
    )
    r = await post_import(seeded_client, payload)
    assert r.status_code == 422

    after = await export_payload(seeded_client)
    names = [b["name"] for b in after["bikes"]]  # export orders by id
    assert names == ["S-Works Tarmac SL8", "Surly Steamroller"]


async def test_import_preserves_bike_ids_and_upload_alignment(client, uploads_dir):
    """Restored image rows point at uploads/bikes/<id>/ — files copied
    alongside the JSON render again."""
    import pathlib

    bike_dir = pathlib.Path(uploads_dir) / "bikes" / "7"
    bike_dir.mkdir(parents=True)
    (bike_dir / "photo.jpg").write_bytes(b"fake jpeg bytes")

    payload = make_export(
        bikes=[
            make_bike(
                7,
                name="Aligned",
                images=[{"filename": "photo.jpg", "original_name": "photo.jpg"}],
            )
        ]
    )
    r = await post_import(client, payload)
    assert r.status_code == 200
    assert r.json() == {"bikes": 1, "pills": 0, "images": 1, "maintenance": 0}

    img = await client.get("/api/images/7/photo.jpg")
    assert img.status_code == 200
