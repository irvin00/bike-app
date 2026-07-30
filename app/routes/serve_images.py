from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

UPLOADS_DIR = Path(__file__).parent.parent.parent / "uploads"

router = APIRouter(prefix="/api/images", tags=["images"])


@router.get("/{bike_id}/{filename}")
async def serve_image(bike_id: int, filename: str):
    filepath = UPLOADS_DIR / "bikes" / str(bike_id) / filename
    if not filepath.is_file():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(str(filepath))
