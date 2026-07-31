import asyncio

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from pydantic import BaseModel
from typing import Optional

from app.image_store import (
    MAX_IMAGE_BYTES,
    image_store,
    process_image_bytes,
    thumb_filename,
)

router = APIRouter(prefix="/api/bikes/{bike_id}/images", tags=["images"])


async def _fetchone(db, sql: str, params: tuple = ()):
    """Execute SQL and return a single row as dict, or None."""
    cursor = await db.execute(sql, params)
    row = await cursor.fetchone()
    return dict(row) if row else None


def _serialize(row: dict, bike_id: int) -> dict:
    return {
        **row,
        "url": f"/api/images/{bike_id}/{row['filename']}",
        "thumb_url": f"/api/images/{bike_id}/{thumb_filename(row['filename'])}",
    }


@router.post("", status_code=201)
async def upload_images(
    request: Request, bike_id: int, files: list[UploadFile] = File(...)
):
    db = request.app.state.db
    bike = await _fetchone(db, "SELECT id FROM bikes WHERE id = ?", (bike_id,))
    if bike is None:
        raise HTTPException(status_code=404, detail="Bike not found")

    # Pass 1: read + validate every file in memory. Nothing is written yet —
    # one bad file rejects the whole batch with zero files on disk, zero rows.
    prepared = []  # (full_jpeg, thumb_jpeg, original_name)
    for upload in files:
        data = b""
        while chunk := await upload.read(1024 * 1024):
            data += chunk
            if len(data) > MAX_IMAGE_BYTES:
                raise HTTPException(
                    status_code=400,
                    detail=f"{upload.filename}: file exceeds 25MB limit",
                )
        if not data:
            raise HTTPException(status_code=400, detail=f"{upload.filename}: empty file")
        # Cheap first filter; content_type is client-supplied and spoofable.
        # Pillow's open/decode is the real gate (also catches decompression bombs).
        if not (upload.content_type or "").startswith("image/"):
            raise HTTPException(
                status_code=400, detail=f"{upload.filename}: not an image file"
            )
        try:
            full_jpeg, thumb_jpeg = await asyncio.to_thread(
                process_image_bytes, data
            )
        except ValueError:
            raise HTTPException(
                status_code=400, detail=f"{upload.filename}: Not a valid image"
            )
        prepared.append((full_jpeg, thumb_jpeg, upload.filename or "image"))
        await upload.close()

    cursor = await db.execute(
        "SELECT COALESCE(MAX(sort_order), -1), COUNT(*) FROM images WHERE bike_id = ?",
        (bike_id,),
    )
    max_sort, count = await cursor.fetchone()
    base = max_sort + 1
    first = count == 0

    # Pass 2: write files + insert rows, then one commit.
    created_ids = []
    for i, (full_jpeg, thumb_jpeg, original_name) in enumerate(prepared):
        name, _ = await asyncio.to_thread(
            image_store.save_processed, bike_id, original_name, full_jpeg, thumb_jpeg
        )
        cursor = await db.execute(
            """INSERT INTO images (bike_id, filename, original_name, is_primary, sort_order)
               VALUES (?, ?, ?, ?, ?)""",
            (bike_id, name, original_name, 1 if first and i == 0 else 0, base + i),
        )
        created_ids.append(cursor.lastrowid)
    await db.commit()

    created = []
    for image_id in created_ids:
        row = await _fetchone(db, "SELECT * FROM images WHERE id = ?", (image_id,))
        created.append(_serialize(row, bike_id))
    return created


class ImageUpdate(BaseModel):
    is_primary: Optional[bool] = None
    sort_order: Optional[int] = None


@router.patch("/{image_id}")
async def update_image(
    request: Request, bike_id: int, image_id: int, body: ImageUpdate
):
    db = request.app.state.db
    row = await _fetchone(
        db,
        "SELECT * FROM images WHERE id = ? AND bike_id = ?",
        (image_id, bike_id),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Image not found")

    updates = body.model_dump(exclude_unset=True)
    if not updates:
        return _serialize(row, bike_id)

    if updates.get("is_primary") is True:
        # At-most-one-primary per bike is enforced here (no DB constraint):
        # unset every other image for the bike, then set this one.
        await db.execute(
            "UPDATE images SET is_primary = 0 WHERE bike_id = ?", (bike_id,)
        )
        await db.execute(
            "UPDATE images SET is_primary = 1 WHERE id = ? AND bike_id = ?",
            (image_id, bike_id),
        )
        updates.pop("is_primary")
    elif updates.get("is_primary") is False:
        # Allowed — leaves the bike with no primary; cards fall back to the
        # placeholder. No UI sends this; keeping the API orthogonal is simpler.
        await db.execute(
            "UPDATE images SET is_primary = 0 WHERE id = ? AND bike_id = ?",
            (image_id, bike_id),
        )
        updates.pop("is_primary")

    if "sort_order" in updates:
        await db.execute(
            "UPDATE images SET sort_order = ? WHERE id = ? AND bike_id = ?",
            (updates["sort_order"], image_id, bike_id),
        )

    await db.commit()
    row = await _fetchone(db, "SELECT * FROM images WHERE id = ?", (image_id,))
    return _serialize(row, bike_id)


@router.delete("/{image_id}", status_code=204)
async def delete_image(request: Request, bike_id: int, image_id: int):
    db = request.app.state.db
    row = await _fetchone(
        db,
        "SELECT * FROM images WHERE id = ? AND bike_id = ?",
        (image_id, bike_id),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Image not found")

    await db.execute("DELETE FROM images WHERE id = ?", (image_id,))
    if row["is_primary"]:
        # Promote the lowest sort_order remaining (tie-break: oldest id).
        # The client mirrors this rule locally — keep the two in sync.
        cand = await _fetchone(
            db,
            "SELECT id FROM images WHERE bike_id = ? ORDER BY sort_order, id LIMIT 1",
            (bike_id,),
        )
        if cand:
            await db.execute(
                "UPDATE images SET is_primary = 1 WHERE id = ?", (cand["id"],)
            )
    await db.commit()

    # DB first, then files — a failed unlink leaves a harmless orphan,
    # never a dangling DB row.
    image_store.delete(bike_id, row["filename"])
