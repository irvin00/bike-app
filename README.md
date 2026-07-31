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
