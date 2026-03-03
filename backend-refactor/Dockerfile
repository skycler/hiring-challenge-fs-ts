FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS base

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev --no-cache
COPY src/ ./src/

# ---------------------------------------------------------------------------
# test — add dev deps, copy tests, run the suite
# ---------------------------------------------------------------------------
FROM base AS test

RUN uv sync --frozen --no-install-project --no-cache

COPY tests/ ./tests/

RUN uv run pytest --tb=short -q

# ---------------------------------------------------------------------------
# production — prod deps + source + data, no test code
# ---------------------------------------------------------------------------
FROM base AS production

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY data/ ./data/

RUN groupadd --system app && useradd --system --gid app app \
    && chown -R app:app /app
USER app

EXPOSE 8000

ENV PATH="/app/.venv/bin:$PATH"

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "src"]
