"""Full database export as a nested JSON document.

GET /api/export composes the shape the UI shows: every bike with its pills,
images (with url/thumb_url), and maintenance records, plus the pill catalog.
Sent with Content-Disposition so a plain link downloads the file.
"""

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Request, Response

from app.routes.bikes import _bike_with_pills, _fetchall, _serialize_image

router = APIRouter(tags=["export"])


@router.get("/api/export")
async def export_all(request: Request):
    db = request.app.state.db

    bikes = await _fetchall(db, "SELECT * FROM bikes ORDER BY id")
    pills = await _fetchall(db, "SELECT * FROM pills ORDER BY label")

    for bike in bikes:
        await _bike_with_pills(db, bike)
        images = await _fetchall(
            db,
            "SELECT * FROM images WHERE bike_id = ? ORDER BY is_primary DESC, sort_order, id",
            (bike["id"],),
        )
        bike["images"] = [_serialize_image(r, bike["id"]) for r in images]
        bike["maintenance_records"] = await _fetchall(
            db,
            "SELECT * FROM maintenance_records WHERE bike_id = ? ORDER BY date DESC",
            (bike["id"],),
        )

    payload = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "pills": pills,
        "bikes": bikes,
    }
    body = json.dumps(payload, indent=2)
    return Response(
        content=body,
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="bike_view.json"'},
    )
