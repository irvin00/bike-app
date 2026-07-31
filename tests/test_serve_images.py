"""Image serving: FileResponse, thumb->full fallback, traversal rejection.

serve_images is filesystem-only (no DB access), so fixture files are
written straight into the tmp uploads dir — no Pillow processing needed.
"""

from fixtures import (
    client,
    image_bytes,
    seeded_client,
    tmp_db_path,
    uploads_dir,
)


async def _write(uploads_dir, bike_id, name, data=b"fake-jpeg-bytes"):
    bike_dir = uploads_dir / "bikes" / str(bike_id)
    bike_dir.mkdir(parents=True, exist_ok=True)
    (bike_dir / name).write_bytes(data)
    return bike_dir


async def test_serve_existing(client, uploads_dir):
    await _write(uploads_dir, 1, "photo.jpg")
    r = await client.get("/api/images/1/photo.jpg")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/jpeg"
    assert r.content == b"fake-jpeg-bytes"


async def test_thumb_fallback(client, uploads_dir):
    # Only the full-size file on disk; a .thumb.jpg request falls back to it.
    await _write(uploads_dir, 1, "photo.jpg")
    r = await client.get("/api/images/1/photo.thumb.jpg")
    assert r.status_code == 200


async def test_missing_404(client, uploads_dir):
    r = await client.get("/api/images/1/nope.jpg")
    assert r.status_code == 404


async def test_traversal_rejected(client, uploads_dir):
    # %2F decodes to "/" inside the filename segment; the route's ".." check
    # must reject it regardless of what exists on disk.
    await _write(uploads_dir, 1, "photo.jpg")
    r = await client.get("/api/images/1/..%2Fapp%2Fmain.py")
    assert r.status_code == 404


async def test_serve_needs_no_db_row(client, uploads_dir):
    # Serving is filesystem-only: a file under a bike_id with no DB row still 200s.
    await _write(uploads_dir, 99, "orphan.jpg")
    r = await client.get("/api/images/99/orphan.jpg")
    assert r.status_code == 200
