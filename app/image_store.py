"""Local image storage + Pillow processing pipeline.

No FastAPI imports here so routes can import it freely. The ImageStore
protocol is the seam for a future S3-backed store (spec §5 Phase 2).
"""

import re
import shutil
import uuid
from io import BytesIO
from pathlib import Path
from typing import Protocol

from PIL import Image, ImageOps, UnidentifiedImageError

UPLOADS_DIR = Path(__file__).parent.parent / "uploads"

MAX_IMAGE_BYTES = 25 * 1024 * 1024  # raw encoded bytes per upload
MAX_DIMENSION = 2000  # spec §5: resize to max 2000px on the long edge
THUMB_DIMENSION = 1024  # spec §5: thumbnail


def thumb_filename(filename: str) -> str:
    """Derive the thumbnail filename for a stored image."""
    return filename.rsplit(".", 1)[0] + ".thumb.jpg"


def _sanitize_stem(original_name: str) -> str:
    """Server never trusts the client filename; keep a safe readable stem."""
    stem = Path(original_name or "image").stem
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem)
    stem = stem.strip("._-")[:60] or "image"
    return stem


def process_image_bytes(data: bytes) -> tuple[bytes, bytes]:
    """Validate, resize, and re-encode an image.

    Returns (full_jpeg, thumb_jpeg). Raises ValueError for anything that
    is not a decodable image. No side effects — callers can validate a
    whole batch before writing a single file.
    """
    try:
        with Image.open(BytesIO(data)) as img:
            img = ImageOps.exif_transpose(img)  # honor EXIF orientation
            img.load()  # force decode so corrupt files fail here, pre-write
            img = _to_rgb(img)
            full = _resize(img, MAX_DIMENSION)
            thumb = _resize(img, THUMB_DIMENSION)
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError) as e:
        raise ValueError("Not a valid image") from e
    return _jpeg_bytes(full), _jpeg_bytes(thumb)


def _to_rgb(img: Image.Image) -> Image.Image:
    if img.mode == "RGB":
        return img
    if img.mode == "RGBA":
        bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
        return Image.alpha_composite(bg, img).convert("RGB")  # white, not black
    return img.convert("RGB")  # P, CMYK, L, ... all → RGB


def _resize(img: Image.Image, bound: int) -> Image.Image:
    copy = img.copy()
    copy.thumbnail((bound, bound), Image.LANCZOS)  # never upscales
    return copy


def _jpeg_bytes(img: Image.Image) -> bytes:
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=85, optimize=True)
    return buf.getvalue()


class ImageStore(Protocol):
    def save(self, bike_id: int, original_name: str, data: bytes) -> tuple[str, str]: ...

    def delete(self, bike_id: int, filename: str) -> None: ...

    def delete_bike_dir(self, bike_id: int) -> None: ...


class LocalImageStore:
    def __init__(self, base_dir: Path = UPLOADS_DIR):
        self.base_dir = base_dir

    def _bike_dir(self, bike_id: int) -> Path:
        return self.base_dir / "bikes" / str(bike_id)

    def _new_name(self, original_name: str) -> str:
        return f"{uuid.uuid4().hex}-{_sanitize_stem(original_name)}.jpg"

    def save(self, bike_id: int, original_name: str, data: bytes) -> tuple[str, str]:
        """Process + write both files. Returns (filename, thumb_filename)."""
        full, thumb = process_image_bytes(data)  # ValueError propagates
        return self.save_processed(bike_id, original_name, full, thumb)

    def save_processed(
        self, bike_id: int, original_name: str, full_jpeg: bytes, thumb_jpeg: bytes
    ) -> tuple[str, str]:
        """Write pre-processed JPEGs. Returns (filename, thumb_filename).

        Split from save() so callers can validate a whole batch first
        (all-or-nothing uploads) before any file is written.
        """
        name = self._new_name(original_name)
        bike_dir = self._bike_dir(bike_id)
        bike_dir.mkdir(parents=True, exist_ok=True)  # uploads/ created here
        (bike_dir / name).write_bytes(full_jpeg)
        (bike_dir / thumb_filename(name)).write_bytes(thumb_jpeg)
        return name, thumb_filename(name)

    def delete(self, bike_id: int, filename: str) -> None:
        bike_dir = self._bike_dir(bike_id)
        for f in (filename, thumb_filename(filename)):
            (bike_dir / f).unlink(missing_ok=True)

    def delete_bike_dir(self, bike_id: int) -> None:
        shutil.rmtree(self._bike_dir(bike_id), ignore_errors=True)


image_store = LocalImageStore()
