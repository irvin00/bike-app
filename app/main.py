from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader

from app.db import get_db, init_db
from app.routes import bikes, pages, serve_images

BASE_DIR = Path(__file__).parent.parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = await get_db()
    await init_db(db)
    app.state.db = db
    yield
    await db.close()


app = FastAPI(lifespan=lifespan)

static_dir = BASE_DIR / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

templates = Environment(
    loader=FileSystemLoader(str(BASE_DIR / "app" / "templates")),
    autoescape=True,
)
app.state.templates = templates

app.include_router(pages.router)
app.include_router(bikes.router)
app.include_router(serve_images.router)
