FROM ghcr.io/astral-sh/uv:python3.14-trixie-slim

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

# Install dependencies first so rebuilds reuse this layer.
# (No --mount flags: they require BuildKit, which old Docker engines lack.)
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY . /app

RUN uv sync --locked --no-dev

# Runtime state lives in volumes mounted over these dirs (see compose.yaml).
RUN useradd --create-home --uid 1000 appuser && \
    mkdir -p /app/data /app/uploads && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
