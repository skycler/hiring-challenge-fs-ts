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
# production — prod deps + source only, no test code
# ---------------------------------------------------------------------------
FROM base AS production

EXPOSE 8000

ENV PATH="/app/.venv/bin:$PATH"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "src"]
