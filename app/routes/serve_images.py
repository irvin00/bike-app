from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.image_store import UPLOADS_DIR

router = APIRouter(prefix="/api/images", tags=["images"])


@router.get("/{bike_id}/{filename}")
async def serve_image(bike_id: int, filename: str):
    # Defense in depth: path params can't contain "/", but reject the rest.
    if not filename or "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=404, detail="Image not found")
    filepath = UPLOADS_DIR / "bikes" / str(bike_id) / filename
    if not filepath.is_file():
        # Thumb requested but absent (seed images, pre-Phase-6 uploads):
        # fall back to the full-size file so nothing breaks — no migration.
        if filename.endswith(".thumb.jpg"):
            alt = UPLOADS_DIR / "bikes" / str(bike_id) / filename.replace(
                ".thumb.jpg", ".jpg"
            )
            if alt.is_file():
                return FileResponse(str(alt))
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(str(filepath))
