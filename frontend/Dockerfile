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
