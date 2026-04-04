# Build Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 优化前后端 Docker 构建速度，升级到 Python 3.12，保持 MongoDB 数据持久化

**Architecture:** 使用多阶段构建 + BuildKit 缓存挂载，后端改用 python:3.12-slim 减小镜像体积，前后端均启用依赖缓存

**Tech Stack:** Docker, Docker Compose, Python 3.12, uv, pnpm, Node 22

---

## File Structure

| File | Purpose |
|------|---------|
| `backend/Dockerfile` | 后端多阶段构建，Python 3.12-slim，uv 缓存 |
| `frontend/Dockerfile` | 前端构建，pnpm 缓存挂载 |
| `docker-compose.yml` | 生产/部署配置 |
| `docker-compose.override.yml` | 开发环境覆盖配置，watch 模式 |
| `backend/pyproject.toml` | Python 版本要求更新 |

---

### Task 1: Update backend Python version requirement

**Files:**
- Modify: `backend/pyproject.toml:5`

- [ ] **Step 1: Update Python version constraint**

```toml
requires-python = ">=3.12,<4.0"
```

- [ ] **Step 2: Commit**

```bash
git add backend/pyproject.toml
git commit -m "chore: update Python version requirement to 3.12"
```

---

### Task 2: Optimize backend Dockerfile with multi-stage build

**Files:**
- Modify: `backend/Dockerfile`

- [ ] **Step 1: Rewrite backend Dockerfile**

```dockerfile
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

WORKDIR /app/backend/

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/backend /app/backend

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
```

- [ ] **Step 2: Commit**

```bash
git add backend/Dockerfile
git commit -m "feat: optimize backend Dockerfile with multi-stage build and Python 3.12"
```

---

### Task 3: Optimize frontend Dockerfile with pnpm cache

**Files:**
- Modify: `frontend/Dockerfile`

- [ ] **Step 1: Rewrite frontend Dockerfile**

```dockerfile
# Stage 0: Build
FROM node:22-slim AS build-stage

ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable

WORKDIR /app/frontend

# Copy package files
COPY frontend/package.json frontend/pnpm-lock.yaml /app/frontend/

# Install dependencies with cache mount
RUN --mount=type=cache,target=/pnpm/store \
    pnpm install --frozen-lockfile

# Copy source and build
COPY ./frontend /app/frontend
ARG VITE_API_URL

RUN pnpm run build

# Stage 1: Production
FROM nginx:1-alpine

COPY --from=build-stage /app/frontend/dist/ /usr/share/nginx/html
COPY ./frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY ./frontend/nginx-backend-not-found.conf /etc/nginx/extra-conf.d/backend-not-found.conf
```

- [ ] **Step 2: Commit**

```bash
git add frontend/Dockerfile
git commit -m "feat: optimize frontend Dockerfile with pnpm cache mount"
```

---

### Task 4: Update docker-compose.override.yml for watch mode

**Files:**
- Modify: `docker-compose.override.yml`

- [ ] **Step 1: Update backend service with optimized watch config**

Replace the backend service section (lines 53-78):

```yaml
  backend:
    restart: "no"
    ports:
      - "8000:8000"
    build:
      context: .
      dockerfile: backend/Dockerfile
      target: runtime
    command:
      - fastapi
      - run
      - --reload
      - "app/main.py"
    develop:
      watch:
        - path: ./backend/app
          action: sync
          target: /app/backend/app
          ignore:
            - "**/__pycache__"
            - "**/*.pyc"
        - path: ./backend/pyproject.toml
          action: rebuild
    volumes:
      - ./backend/htmlcov:/app/backend/htmlcov
    environment:
      SMTP_HOST: "mailcatcher"
      SMTP_PORT: "1025"
      SMTP_TLS: "false"
      EMAILS_FROM_EMAIL: "noreply@example.com"
```

- [ ] **Step 2: Update frontend service for development**

Replace the frontend service section (lines 103-112):

```yaml
  frontend:
    restart: "no"
    ports:
      - "5173:80"
    build:
      context: .
      dockerfile: frontend/Dockerfile
      target: build-stage
      args:
        - VITE_API_URL=http://100.121.41.112:8000
        - NODE_ENV=development
```

- [ ] **Step 3: Commit**

```bash
git add docker-compose.override.yml
git commit -m "chore: update docker-compose.override.yml for optimized watch mode"
```

---

### Task 5: Verify MongoDB data persistence

**Files:**
- Check: `docker-compose.yml:25`

- [ ] **Step 1: Verify MongoDB volume is configured**

确认 `docker-compose.yml` 中 MongoDB 服务已有数据卷：

```yaml
  mongodb:
    image: mongo:7
    restart: always
    volumes:
      - app-db-data:/data/db
```

以及文件末尾的 volumes 定义：

```yaml
volumes:
  app-db-data:
  app-regis-data:
```

- [ ] **Step 2: 如果配置正确，无需修改，直接标记完成**

---

### Task 6: Test build optimization

- [ ] **Step 1: 测试后端构建**

```bash
cd /home/smith/Project/full-stack-fastapi-template
docker compose build backend --no-cache
```

预期：构建成功，镜像体积明显减小（从 ~1GB 降至 ~400-500MB）

- [ ] **Step 2: 测试前端构建**

```bash
docker compose build frontend --no-cache
```

预期：构建成功，pnpm 依赖安装使用缓存

- [ ] **Step 3: 测试完整启动**

```bash
docker compose watch
```

或（如果不支持 watch）：

```bash
docker compose up -d --build
```

- [ ] **Step 4: 验证服务可访问**

```bash
curl http://localhost:8000/api/v1/utils/health-check/
# 应返回 true

curl -s http://localhost:5173/ > /dev/null && echo "Frontend OK"
# 应输出 Frontend OK
```

- [ ] **Step 5: Commit 最终变更**

```bash
git add -A
git commit -m "feat: complete build optimization with Python 3.12 and multi-stage builds"
```

---

## Self-Review Checklist

- [x] Python 3.12 升级：Task 1 更新 pyproject.toml
- [x] 后端多阶段构建：Task 2 使用 python:3.12-slim
- [x] 前端缓存优化：Task 3 使用 pnpm cache mount
- [x] Watch 模式配置：Task 4 更新 override 文件
- [x] MongoDB 持久化：Task 5 确认数据卷配置
- [x] 构建测试：Task 6 验证所有服务

---

## Expected Improvements

| 指标 | 优化前 | 优化后（预估） |
|------|--------|---------------|
| 后端镜像大小 | ~1.2 GB | ~500 MB |
| 前端构建时间 | ~60s | ~40s（缓存命中）|
| 后端构建时间 | ~120s | ~80s（缓存命中）|
| Python 版本 | 3.10 | 3.12 |
