# Bike View

A personal bike directory to track bikes you own and have owned — with
maintenance records, images, and tags. FastAPI + SQLite + Jinja2, vanilla
JS, no frontend framework.

## Quick start

Requires [uv](https://docs.astral.sh/uv/) (installs Python 3.14 automatically).

```bash
uv sync
./bike          # interactive menu: start / stop / restart / open
```

or directly:

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open http://127.0.0.1:8000 — other devices on your network can reach it via
the LAN address the script prints. `./bike` works on macOS and Linux
(Linux needs `iproute2`; the open command uses `xdg-open`).

- **Database**: SQLite, auto-created at `data/bike_view.db` on first start
- **Demo data**: `uv run python -m app.seed`
- **Tests**: `uv run pytest`

## Docker

```bash
docker compose up -d --build
```

Open http://127.0.0.1:8000. Optional demo data (once):

```bash
docker compose run --rm bike-view uv run python -m app.seed
```

The SQLite DB and uploaded images live in named volumes (`docker volume ls`
to find them) — they survive rebuilds. Back them up with e.g.:

```bash
docker run --rm -v bike_view_bike-data:/data -v "$PWD":/backup \
  alpine cp -r /data /backup/data-backup
```

Don't run `./bike` while the container is up — both bind port 8000, and the
script's status check can't see the containerized server.
