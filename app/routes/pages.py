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


@router.get("/bikes/new", response_class=HTMLResponse)
async def bike_new(request: Request):
    env = request.app.state.templates
    db = request.app.state.db

    cursor = await db.execute("SELECT * FROM pills ORDER BY label")
    all_pills = [dict(r) for r in await cursor.fetchall()]

    template = env.get_template("bike_form.html.j2")
    html = template.render(
        request=request, mode="create",
        bike=None, all_pills=all_pills,
        bike_pills=None, images=None,
    )
    return HTMLResponse(html)


@router.get("/bikes/{bike_id}", response_class=HTMLResponse)
async def bike_detail(request: Request, bike_id: int):
    env = request.app.state.templates
    db = request.app.state.db

    cursor = await db.execute(
        "SELECT * FROM bikes WHERE id = ?", (bike_id,)
    )
    bike = await cursor.fetchone()
    if bike is None:
        return HTMLResponse("Bike not found", status_code=404)
    bike = dict(bike)

    # Fetch attached pills
    pc = await db.execute(
        """SELECT p.id, p.label, p.color
           FROM pills p
           JOIN bike_pills bp ON bp.pill_id = p.id
           WHERE bp.bike_id = ?
           ORDER BY p.label""",
        (bike_id,),
    )
    pills = [dict(r) for r in await pc.fetchall()]

    # Fetch images
    ic = await db.execute(
        "SELECT * FROM images WHERE bike_id = ? ORDER BY sort_order",
        (bike_id,),
    )
    images = [dict(r) for r in await ic.fetchall()]

    # Fetch maintenance records
    mc = await db.execute(
        "SELECT * FROM maintenance_records WHERE bike_id = ? ORDER BY date DESC",
        (bike_id,),
    )
    maintenance = [dict(r) for r in await mc.fetchall()]

    template = env.get_template("bike_detail.html.j2")
    html = template.render(
        request=request, bike=bike, pills=pills,
        images=images, maintenance=maintenance,
    )
    return HTMLResponse(html)


@router.get("/bikes/{bike_id}/edit", response_class=HTMLResponse)
async def bike_edit(request: Request, bike_id: int):
    env = request.app.state.templates
    db = request.app.state.db

    cursor = await db.execute(
        "SELECT * FROM bikes WHERE id = ?", (bike_id,)
    )
    bike = await cursor.fetchone()
    if bike is None:
        return HTMLResponse("Bike not found", status_code=404)
    bike = dict(bike)

    # Fetch all pills (for the checkbox list)
    pc = await db.execute("SELECT * FROM pills ORDER BY label")
    all_pills = [dict(r) for r in await pc.fetchall()]

    # Fetch attached pills (for pre-checking)
    bpc = await db.execute(
        """SELECT p.id, p.label, p.color
           FROM pills p
           JOIN bike_pills bp ON bp.pill_id = p.id
           WHERE bp.bike_id = ?
           ORDER BY p.label""",
        (bike_id,),
    )
    bike_pills = [dict(r) for r in await bpc.fetchall()]

    # Fetch images
    ic = await db.execute(
        "SELECT * FROM images WHERE bike_id = ? ORDER BY sort_order",
        (bike_id,),
    )
    images = [dict(r) for r in await ic.fetchall()]

    template = env.get_template("bike_form.html.j2")
    html = template.render(
        request=request, mode="edit",
        bike=bike, all_pills=all_pills,
        bike_pills=bike_pills, images=images,
    )
    return HTMLResponse(html)
