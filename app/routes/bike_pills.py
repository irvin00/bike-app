from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

router = APIRouter(
    prefix="/api/bikes/{bike_id}/pills", tags=["bike_pills"]
)


class PillSet(BaseModel):
    pill_ids: list[int]


@router.put("")
async def set_pills(request: Request, bike_id: int, body: PillSet):
    db = request.app.state.db

    # Verify bike exists
    cursor = await db.execute(
        "SELECT 1 FROM bikes WHERE id = ?", (bike_id,)
    )
    if await cursor.fetchone() is None:
        raise HTTPException(status_code=404, detail="Bike not found")

    # Atomically replace all pill attachments
    await db.execute(
        "DELETE FROM bike_pills WHERE bike_id = ?", (bike_id,)
    )
    for pid in body.pill_ids:
        await db.execute(
            "INSERT INTO bike_pills (bike_id, pill_id) VALUES (?, ?)",
            (bike_id, pid),
        )
    await db.commit()

    # Return the updated pill list
    cursor = await db.execute(
        """SELECT p.id, p.label, p.color
           FROM pills p
           JOIN bike_pills bp ON bp.pill_id = p.id
           WHERE bp.bike_id = ?
           ORDER BY p.label""",
        (bike_id,),
    )
    return [dict(r) for r in await cursor.fetchall()]
