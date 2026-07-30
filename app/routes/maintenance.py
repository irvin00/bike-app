from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(
    prefix="/api/bikes/{bike_id}/maintenance", tags=["maintenance"]
)


class MaintenanceCreate(BaseModel):
    date: str
    description: str
    cost: Optional[float] = None


class MaintenanceUpdate(BaseModel):
    date: Optional[str] = None
    description: Optional[str] = None
    cost: Optional[float] = None


async def _fetchone(db, sql: str, params: tuple = ()):
    cursor = await db.execute(sql, params)
    row = await cursor.fetchone()
    return dict(row) if row else None


async def _fetchall(db, sql: str, params: tuple = ()) -> list[dict]:
    cursor = await db.execute(sql, params)
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def _bike_exists(db, bike_id: int) -> bool:
    row = await _fetchone(db, "SELECT 1 FROM bikes WHERE id = ?", (bike_id,))
    return row is not None


@router.get("")
async def list_maintenance(request: Request, bike_id: int):
    db = request.app.state.db
    if not await _bike_exists(db, bike_id):
        raise HTTPException(status_code=404, detail="Bike not found")
    return await _fetchall(
        db,
        "SELECT * FROM maintenance_records WHERE bike_id = ? ORDER BY date DESC",
        (bike_id,),
    )


@router.post("", status_code=201)
async def create_maintenance(
    request: Request, bike_id: int, body: MaintenanceCreate
):
    db = request.app.state.db
    if not await _bike_exists(db, bike_id):
        raise HTTPException(status_code=404, detail="Bike not found")

    cursor = await db.execute(
        """INSERT INTO maintenance_records (bike_id, date, description, cost)
           VALUES (?, ?, ?, ?)""",
        (bike_id, body.date, body.description, body.cost),
    )
    await db.commit()
    return await _fetchone(
        db,
        "SELECT * FROM maintenance_records WHERE id = ?",
        (cursor.lastrowid,),
    )


@router.patch("/{record_id}")
async def update_maintenance(
    request: Request, bike_id: int, record_id: int, body: MaintenanceUpdate
):
    db = request.app.state.db
    row = await _fetchone(
        db,
        "SELECT * FROM maintenance_records WHERE id = ? AND bike_id = ?",
        (record_id, bike_id),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Record not found")

    updates = body.model_dump(exclude_unset=True)
    if not updates:
        return row

    set_clause = ", ".join(f"{key} = ?" for key in updates)
    values = list(updates.values())
    await db.execute(
        f"UPDATE maintenance_records SET {set_clause} WHERE id = ? AND bike_id = ?",
        (*values, record_id, bike_id),
    )
    await db.commit()
    return await _fetchone(
        db,
        "SELECT * FROM maintenance_records WHERE id = ?",
        (record_id,),
    )


@router.delete("/{record_id}", status_code=204)
async def delete_maintenance(
    request: Request, bike_id: int, record_id: int
):
    db = request.app.state.db
    cursor = await db.execute(
        "DELETE FROM maintenance_records WHERE id = ? AND bike_id = ?",
        (record_id, bike_id),
    )
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Record not found")
    await db.commit()
