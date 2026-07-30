from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["pages"])


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    env = request.app.state.templates
    db = request.app.state.db

    cursor = await db.execute(
        "SELECT * FROM bikes ORDER BY created_at DESC"
    )
    bikes = [dict(row) for row in await cursor.fetchall()]

    for bike in bikes:
        pc = await db.execute(
            """SELECT p.id, p.label, p.color
               FROM pills p
               JOIN bike_pills bp ON bp.pill_id = p.id
               WHERE bp.bike_id = ?
               ORDER BY p.label""",
            (bike["id"],),
        )
        bike["pills"] = [dict(r) for r in await pc.fetchall()]

        ic = await db.execute(
            """SELECT filename FROM images
               WHERE bike_id = ? AND is_primary = 1
               LIMIT 1""",
            (bike["id"],),
        )
        img = await ic.fetchone()
        bike["primary_image"] = img["filename"] if img else None

    template = env.get_template("index.html.j2")
    html = template.render(request=request, bikes=bikes)
    return HTMLResponse(html)
