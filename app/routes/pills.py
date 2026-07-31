from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/pills", tags=["pills"])


class PillCreate(BaseModel):
    label: str
    color: str = "#6b7280"  # matches DB default in db.py


async def _fetchone(db, sql: str, params: tuple = ()):
    cursor = await db.execute(sql, params)
    row = await cursor.fetchone()
    return dict(row) if row else None


@router.get("")
async def list_pills(request: Request):
    db = request.app.state.db
    cursor = await db.execute("SELECT * FROM pills ORDER BY label")
    return [dict(r) for r in await cursor.fetchall()]


@router.post("", status_code=201)
async def create_pill(request: Request, body: PillCreate):
    db = request.app.state.db
    label = body.label.strip()
    if not label:
        raise HTTPException(status_code=422, detail="Label is required")

    # Guard the UNIQUE constraint on pills.label (else IntegrityError -> 500)
    existing = await _fetchone(
        db, "SELECT 1 FROM pills WHERE label = ?", (label,)
    )
    if existing:
        raise HTTPException(
            status_code=409, detail="A pill with this label already exists"
        )

    cursor = await db.execute(
        "INSERT INTO pills (label, color) VALUES (?, ?)",
        (label, body.color),
    )
    await db.commit()
    return await _fetchone(
        db, "SELECT * FROM pills WHERE id = ?", (cursor.lastrowid,)
    )


@router.delete("/{pill_id}", status_code=204)
async def delete_pill(request: Request, pill_id: int):
    db = request.app.state.db
    cursor = await db.execute("DELETE FROM pills WHERE id = ?", (pill_id,))
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Pill not found")
    await db.commit()
