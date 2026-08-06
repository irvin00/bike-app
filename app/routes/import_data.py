"""Full database restore from a bike_view.json export.

POST /api/import accepts the exact shape GET /api/export produces. It is a
full restore: existing rows are deleted, then bikes, pills, bike_pills,
maintenance_records, and images are inserted from the file. Validation is
all-or-nothing — the whole file must pass model + cross-reference checks
before a single row is written (422 with a clear string detail otherwise;
api.js surfaces err.detail verbatim). Image rows restore filenames only —
the user copies uploads/ alongside the JSON; missing files fall back to the
placeholder in the UI.
"""

import json

import aiosqlite
from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from pydantic import BaseModel, ValidationError
from typing import Literal, Optional

router = APIRouter(tags=["import"])

MAX_IMPORT_BYTES = 10 * 1024 * 1024


class PillRow(BaseModel):
    id: int
    label: str
    color: str = "#6b7280"


class PillRef(BaseModel):
    """Nested bike.pills from the export — only the id is load-bearing."""

    id: int
    label: Optional[str] = None
    color: Optional[str] = None


class ImageRow(BaseModel):
    bike_id: Optional[int] = None  # cross-checked against the parent when present
    filename: str
    original_name: str = ""
    is_primary: bool = False  # accepts 0/1/true/false; stored as int()
    sort_order: int = 0
    # id, url, thumb_url, created_at are extra -> ignored by Pydantic


class MaintenanceRow(BaseModel):
    bike_id: Optional[int] = None
    date: str
    description: str
    cost: Optional[float] = None
    # id, created_at extra -> ignored


class BikeRow(BaseModel):
    id: int
    name: str
    status: Literal["active", "former"] = "active"  # protects the DB CHECK
    description: str = ""
    full_story: str = ""
    acquired_on: Optional[str] = None
    retired_on: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    pills: list[PillRef] = []
    images: list[ImageRow] = []
    maintenance_records: list[MaintenanceRow] = []


class ExportData(BaseModel):
    pills: list[PillRow]  # required — a missing key is a 422
    bikes: list[BikeRow]
    # exported_at extra -> ignored


@router.post("/api/import")
async def import_data(request: Request, file: Optional[UploadFile] = File(None)):
    db = request.app.state.db
    if file is None:
        raise HTTPException(status_code=422, detail="No file uploaded")

    # Read in chunks (mirrors images.py); content_type is not trusted —
    # the JSON parse is the real gate.
    raw = b""
    while chunk := await file.read(1024 * 1024):
        raw += chunk
        if len(raw) > MAX_IMPORT_BYTES:
            await file.close()
            raise HTTPException(status_code=422, detail="Import file exceeds 10MB limit")
    await file.close()

    try:
        payload = json.loads(raw)  # bytes OK; handles UTF-8/16/32
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=422, detail="File is not a valid bike_view.json export"
        )

    try:
        data = ExportData.model_validate(payload)
    except ValidationError as exc:
        details = "; ".join(
            f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}"
            for e in exc.errors()[:3]
        )
        raise HTTPException(status_code=422, detail=f"Invalid export file: {details}")

    # Cross-reference validation — pure in-memory, before any DB write.
    pill_ids, pill_labels = set(), set()
    for p in data.pills:
        label = p.label.strip()
        if not label:
            raise HTTPException(status_code=422, detail=f"Pill {p.id}: label must not be empty")
        if p.id in pill_ids:
            raise HTTPException(status_code=422, detail=f"Duplicate pill id {p.id}")
        if label in pill_labels:
            raise HTTPException(status_code=422, detail=f"Duplicate pill label '{label}'")
        pill_ids.add(p.id)
        pill_labels.add(label)
        p.label = label  # insert the stripped value

    bike_ids = set()
    for b in data.bikes:
        if b.id in bike_ids:
            raise HTTPException(status_code=422, detail=f"Duplicate bike id {b.id}")
        bike_ids.add(b.id)
        for ref in b.pills:
            if ref.id not in pill_ids:
                raise HTTPException(
                    status_code=422,
                    detail=f"Bike {b.id} references unknown pill id {ref.id}",
                )
        primaries = 0
        for img in b.images:
            if not img.filename or "/" in img.filename or "\\" in img.filename or ".." in img.filename:
                raise HTTPException(
                    status_code=422,
                    detail=f"Bike {b.id}: unsafe image filename '{img.filename}'",
                )
            if img.bike_id not in (None, b.id):
                raise HTTPException(
                    status_code=422,
                    detail=f"Bike {b.id}: image bike_id {img.bike_id} does not match",
                )
            if img.is_primary:
                primaries += 1
        if primaries > 1:
            raise HTTPException(
                status_code=422, detail=f"Bike {b.id}: more than one primary image"
            )
        for rec in b.maintenance_records:
            if rec.bike_id not in (None, b.id):
                raise HTTPException(
                    status_code=422,
                    detail=f"Bike {b.id}: maintenance bike_id {rec.bike_id} does not match",
                )

    # Restore. No explicit BEGIN: aiosqlite's default isolation opens a
    # transaction on the first DML statement; one commit at the end, rollback
    # on any failure so a mid-import error leaves the previous data intact.
    try:
        await db.execute("DELETE FROM bike_pills")
        await db.execute("DELETE FROM maintenance_records")
        await db.execute("DELETE FROM images")
        await db.execute("DELETE FROM bikes")
        await db.execute("DELETE FROM pills")

        for p in data.pills:
            # Idempotent on the unique label; ids are preserved because
            # bike_pills references them.
            await db.execute(
                "INSERT OR IGNORE INTO pills (id, label, color) VALUES (?, ?, ?)",
                (p.id, p.label, p.color),
            )

        for b in data.bikes:
            # Bike ids are preserved so uploads/bikes/<id>/ stays aligned
            # with the file's image filenames. COALESCE keeps explicit NULLs
            # out of created_at/updated_at — NULL rows would sink the home
            # page's ORDER BY created_at DESC.
            await db.execute(
                """INSERT INTO bikes (id, name, description, full_story, status,
                                     acquired_on, retired_on, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, COALESCE(?, datetime('now')),
                           COALESCE(?, datetime('now')))""",
                (b.id, b.name, b.description, b.full_story, b.status,
                 b.acquired_on, b.retired_on, b.created_at, b.updated_at),
            )
            for ref in b.pills:
                await db.execute(
                    "INSERT OR IGNORE INTO bike_pills (bike_id, pill_id) VALUES (?, ?)",
                    (b.id, ref.id),
                )
            for img in b.images:
                await db.execute(
                    """INSERT INTO images (bike_id, filename, original_name,
                                           is_primary, sort_order)
                       VALUES (?, ?, ?, ?, ?)""",
                    (b.id, img.filename, img.original_name, int(img.is_primary),
                     img.sort_order),
                )
            for rec in b.maintenance_records:
                await db.execute(
                    """INSERT INTO maintenance_records (bike_id, date, description, cost)
                       VALUES (?, ?, ?, ?)""",
                    (b.id, rec.date, rec.description, rec.cost),
                )
        await db.commit()
    except aiosqlite.IntegrityError as exc:
        # Defense-in-depth: validation should make this unreachable, but an
        # unexpected constraint violation must not 500 mid-restore.
        await db.rollback()
        raise HTTPException(
            status_code=422,
            detail=f"Import failed: data violates database constraints ({exc})",
        )
    except Exception:
        await db.rollback()  # safe no-op if no transaction was open
        raise

    return {
        "bikes": len(data.bikes),
        "pills": len(data.pills),
        "images": sum(len(b.images) for b in data.bikes),
        "maintenance": sum(len(b.maintenance_records) for b in data.bikes),
    }
