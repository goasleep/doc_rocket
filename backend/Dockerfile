# Stage 1: Builder
FROM python:3.12-slim AS builder

ENV PYTHONUNBUFFERED=1
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/

WORKDIR /app/

# Install dependencies with cache mount
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-workspace --package app

# Copy source code
COPY ./backend/scripts /app/backend/scripts
COPY ./backend/pyproject.toml /app/backend/
COPY ./backend/app /app/backend/app
COPY ./backend/tests /app/backend/tests

# Sync project
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --package app

# Stage 2: Runtime
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1
ENV PATH="/app/.venv/bin:$PATH"

WORKDIR /app/

# Copy virtual environment and backend code from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/backend /app/backend

WORKDIR /app/backend/

# Install system Chromium and dependencies
RUN sed -i 's|http://deb.debian.org|http://mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
    sed -i 's|http://deb.debian.org|http://mirrors.aliyun.com|g' /etc/apt/sources.list && \
    apt-get update && apt-get install -y --no-install-recommends \
        chromium chromium-sandbox \
        libnss3 libnspr4 libdbus-1-3 libatk1.0-0 libatk-bridge2.0-0 \
        libcups2 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
        libgbm1 libxkbcommon0 libasound2 \
    && rm -rf /var/lib/apt/lists/*

CMD ["fastapi", "run", "--workers", "4", "app/main.py"]
