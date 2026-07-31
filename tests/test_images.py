"""Images API: multipart upload, primary selection, sort order, delete.

Seeded bikes already carry image rows whose files don't exist on disk,
so primary/sort tests use a freshly created bike with no images.
"""

from fixtures import (
    client,
    image_bytes,
    seeded_client,
    tmp_db_path,
    uploads_dir,
)

async def _fresh_bike(client) -> int:
    r = await client.post("/api/bikes", json={"name": "Fresh Bike"})
    return r.json()["id"]


async def test_upload_first_becomes_primary(client, uploads_dir, image_bytes):
    bike_id = await _fresh_bike(client)
    r = await client.post(
        f"/api/bikes/{bike_id}/images",
        files=[("files", ("a.jpg", image_bytes, "image/jpeg"))],
    )
    assert r.status_code == 201
    data = r.json()
    assert len(data) == 1
    assert data[0]["is_primary"] == 1
    assert data[0]["sort_order"] == 0
    # Both files landed on disk under the tmp uploads dir.
    bike_dir = uploads_dir / "bikes" / str(bike_id)
    files = sorted(p.name for p in bike_dir.iterdir())
    assert len(files) == 2
    assert any(f.endswith(".jpg") for f in files)
    assert any(f.endswith(".thumb.jpg") for f in files)


async def test_upload_second_not_primary(client, image_bytes):
    bike_id = await _fresh_bike(client)
    for name in ("a.jpg", "b.jpg"):
        r = await client.post(
            f"/api/bikes/{bike_id}/images",
            files=[("files", (name, image_bytes, "image/jpeg"))],
        )
        assert r.status_code == 201
    created = [img for img in r.json()]
    assert [img["is_primary"] for img in created] == [0]
    bike = (await client.get(f"/api/bikes/{bike_id}")).json()
    assert [img["is_primary"] for img in bike["images"]] == [1, 0]
    assert [img["sort_order"] for img in bike["images"]] == [0, 1]


async def test_upload_batch_all_or_nothing(client, uploads_dir, image_bytes):
    bike_id = await _fresh_bike(client)
    r = await client.post(
        f"/api/bikes/{bike_id}/images",
        files=[
            ("files", ("a.jpg", image_bytes, "image/jpeg")),
            ("files", ("b.txt", b"hello", "text/plain")),
        ],
    )
    assert r.status_code == 400
    assert "not an image file" in r.json()["detail"]
    # One bad file rejects the whole batch: no rows, no files on disk.
    bike = (await client.get(f"/api/bikes/{bike_id}")).json()
    assert bike["images"] == []
    assert not (uploads_dir / "bikes" / str(bike_id)).exists()


async def test_upload_non_image(client):
    bike_id = await _fresh_bike(client)
    r = await client.post(
        f"/api/bikes/{bike_id}/images",
        files=[("files", ("x.txt", b"hello", "text/plain"))],
    )
    assert r.status_code == 400


async def test_upload_empty_file(client):
    bike_id = await _fresh_bike(client)
    r = await client.post(
        f"/api/bikes/{bike_id}/images",
        files=[("files", ("empty.jpg", b"", "image/jpeg"))],
    )
    assert r.status_code == 400
    assert "empty file" in r.json()["detail"]


async def test_upload_bike_404(client, image_bytes):
    r = await client.post(
        "/api/bikes/999/images",
        files=[("files", ("a.jpg", image_bytes, "image/jpeg"))],
    )
    assert r.status_code == 404


async def test_patch_primary_unsets_others(client, image_bytes):
    bike_id = await _fresh_bike(client)
    for name in ("a.jpg", "b.jpg"):
        await client.post(
            f"/api/bikes/{bike_id}/images",
            files=[("files", (name, image_bytes, "image/jpeg"))],
        )
    bike = (await client.get(f"/api/bikes/{bike_id}")).json()
    second = bike["images"][1]["id"]
    r = await client.patch(
        f"/api/bikes/{bike_id}/images/{second}", json={"is_primary": True}
    )
    assert r.status_code == 200
    assert r.json()["is_primary"] == 1
    bike = (await client.get(f"/api/bikes/{bike_id}")).json()
    assert [img["is_primary"] for img in bike["images"]] == [1, 0]
    assert bike["images"][0]["id"] == second


async def test_patch_sort_order(client, image_bytes):
    bike_id = await _fresh_bike(client)
    await client.post(
        f"/api/bikes/{bike_id}/images",
        files=[("files", ("a.jpg", image_bytes, "image/jpeg"))],
    )
    bike = (await client.get(f"/api/bikes/{bike_id}")).json()
    img_id = bike["images"][0]["id"]
    r = await client.patch(
        f"/api/bikes/{bike_id}/images/{img_id}", json={"sort_order": 5}
    )
    assert r.status_code == 200
    assert r.json()["sort_order"] == 5


async def test_patch_404(client):
    r = await client.patch("/api/bikes/1/images/999", json={"is_primary": True})
    assert r.status_code == 404


async def test_delete_removes_files(client, uploads_dir, image_bytes):
    bike_id = await _fresh_bike(client)
    await client.post(
        f"/api/bikes/{bike_id}/images",
        files=[("files", ("a.jpg", image_bytes, "image/jpeg"))],
    )
    bike = (await client.get(f"/api/bikes/{bike_id}")).json()
    img_id = bike["images"][0]["id"]
    r = await client.delete(f"/api/bikes/{bike_id}/images/{img_id}")
    assert r.status_code == 204
    bike = (await client.get(f"/api/bikes/{bike_id}")).json()
    assert bike["images"] == []
    files = list((uploads_dir / "bikes" / str(bike_id)).iterdir())
    assert files == []  # full + thumb both unlinked


async def test_delete_primary_promotes_first(client, image_bytes):
    bike_id = await _fresh_bike(client)
    for name in ("a.jpg", "b.jpg"):
        await client.post(
            f"/api/bikes/{bike_id}/images",
            files=[("files", (name, image_bytes, "image/jpeg"))],
        )
    bike = (await client.get(f"/api/bikes/{bike_id}")).json()
    first, second = bike["images"]
    assert first["is_primary"] == 1
    r = await client.delete(f"/api/bikes/{bike_id}/images/{first['id']}")
    assert r.status_code == 204
    remaining = (await client.get(f"/api/bikes/{bike_id}")).json()["images"]
    assert [img["id"] for img in remaining] == [second["id"]]
    assert remaining[0]["is_primary"] == 1  # promoted


async def test_delete_404(client):
    r = await client.delete("/api/bikes/1/images/999")
    assert r.status_code == 404
