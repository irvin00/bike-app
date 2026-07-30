from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/bikes", tags=["bikes"])


class BikeCreate(BaseModel):
    name: str
    description: str = ""
    full_story: str = ""
    status: str = "active"
    acquired_on: Optional[str] = None
    retired_on: Optional[str] = None


class BikeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    full_story: Optional[str] = None
    status: Optional[str] = None
    acquired_on: Optional[str] = None
    retired_on: Optional[str] = None


async def _fetchone(db, sql: str, params: tuple = ()):
    """Execute SQL and return a single row as dict, or None."""
    cursor = await db.execute(sql, params)
    row = await cursor.fetchone()
    return dict(row) if row else None


async def _fetchall(db, sql: str, params: tuple = ()) -> list[dict]:
    """Execute SQL and return all rows as dicts."""
    cursor = await db.execute(sql, params)
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def _attach_pills(db, bike: dict) -> dict:
    rows = await _fetchall(
        db,
        """SELECT p.id, p.label, p.color
           FROM pills p
           JOIN bike_pills bp ON bp.pill_id = p.id
           WHERE bp.bike_id = ?
           ORDER BY p.label""",
        (bike["id"],),
    )
    bike["pills"] = rows
    return bike


async def _bike_with_pills(db, row: dict | None) -> dict | None:
    if row is None:
        return None
    return await _attach_pills(db, row)


@router.get("")
async def list_bikes(request: Request, status: Optional[str] = None):
    db = request.app.state.db
    if status and status in ("active", "former"):
        rows = await _fetchall(db,
            "SELECT * FROM bikes WHERE status = ? ORDER BY created_at DESC",
            (status,),
        )
    else:
        rows = await _fetchall(db,
            "SELECT * FROM bikes ORDER BY created_at DESC"
        )
    return [await _bike_with_pills(db, row) for row in rows]


@router.get("/{bike_id}")
async def get_bike(request: Request, bike_id: int):
    db = request.app.state.db
    row = await _fetchone(db,
        "SELECT * FROM bikes WHERE id = ?", (bike_id,)
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Bike not found")
    return await _bike_with_pills(db, row)


@router.post("", status_code=201)
async def create_bike(request: Request, body: BikeCreate):
    db = request.app.state.db
    cursor = await db.execute(
        """INSERT INTO bikes (name, description, full_story, status, acquired_on, retired_on)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (body.name, body.description, body.full_story, body.status,
         body.acquired_on, body.retired_on),
    )
    await db.commit()
    row = await _fetchone(db,
        "SELECT * FROM bikes WHERE id = ?", (cursor.lastrowid,)
    )
    return await _bike_with_pills(db, row)


@router.patch("/{bike_id}")
async def update_bike(request: Request, bike_id: int, body: BikeUpdate):
    db = request.app.state.db
    row = await _fetchone(db,
        "SELECT * FROM bikes WHERE id = ?", (bike_id,)
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Bike not found")

    updates = body.model_dump(exclude_unset=True)
    if not updates:
        return await _bike_with_pills(db, row)

    set_clause = ", ".join(
        f"{key} = ?" if key != "updated_at" else "updated_at = datetime('now')"
        for key in updates
    )
    values = [v for k, v in updates.items() if k != "updated_at"]
    updates["updated_at"] = "datetime('now')"  # signal for the set_clause

    await db.execute(
        f"UPDATE bikes SET {set_clause} WHERE id = ?",
        (*values, bike_id),
    )
    await db.commit()

    row = await _fetchone(db,
        "SELECT * FROM bikes WHERE id = ?", (bike_id,)
    )
    return await _bike_with_pills(db, row)


@router.delete("/{bike_id}", status_code=204)
async def delete_bike(request: Request, bike_id: int):
    db = request.app.state.db
    cursor = await db.execute(
        "DELETE FROM bikes WHERE id = ?", (bike_id,)
    )
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Bike not found")
    await db.commit()
