# Docker-based Development Environment

This project uses Docker for all development operations. You only need Docker and Make installed locally.

## Prerequisites

- Docker (with Compose v2.22+)
- Make

No need to install Python, Node.js, uv, or pnpm locally!

## Quick Start

```bash
# 1. Clone and enter the project
git clone <repo-url>
cd full-stack-fastapi-template

# 2. Create environment file
cp .env.example .env
# Edit .env with your configuration

# 3. Start development environment
make dev
```

Services will be available at:
- Backend API: http://localhost:8000
- Frontend: http://localhost:5173
- Flower (Celery): http://localhost:5555
- MongoDB: localhost:27017
- Redis: localhost:6379

## Available Commands

### Build & Infrastructure

```bash
make build              # Build all Docker images
make build-backend      # Build backend only
make build-frontend     # Build frontend only
make rebuild            # Rebuild without cache
```

### Development

```bash
make up                 # Start all services (detached)
make dev                # Start with live-reload (recommended)
make stop               # Stop services
make down               # Stop and remove containers
make down-volumes       # Stop and remove containers + volumes (WARNING: data loss)
make restart            # Restart all services
```

### Logs & Debugging

```bash
make logs               # Show all logs
make logs-backend       # Backend logs
make logs-frontend      # Frontend logs
make logs-celery        # Celery worker logs
make ps                 # Show running containers
make status             # Check service health
```

### Shell Access

```bash
make shell-backend      # Open shell in backend container
make shell-frontend     # Open shell in frontend container
make shell-mongodb      # Open MongoDB shell
make shell-redis        # Open Redis CLI
```

### Testing (All run inside containers)

```bash
make test               # Run all tests
make test-backend       # Backend tests
make test-backend-watch # Backend tests (watch mode)
make test-frontend      # Frontend E2E tests
make test-frontend-ui   # Frontend E2E tests (UI mode)
```

### Code Quality

```bash
make lint               # Run all linters
make lint-backend       # Backend lint (mypy + ruff)
make lint-frontend      # Frontend lint (biome)
make format             # Format all code
make format-backend     # Format backend
make format-frontend    # Format frontend
make check              # Run all checks (lint + test)
```

### Code Generation

```bash
make generate-client    # Generate OpenAPI client (backend -> frontend)
make generate-routes    # Generate TanStack Router routes
```

### Package Management

```bash
# Backend (Python)
make add-backend PACKAGE=requests       # Add production package
make dev-backend PACKAGE=pytest         # Add dev package

# Frontend (Node.js)
make add-frontend PACKAGE=lodash        # Add production package
make dev-frontend PACKAGE=@types/lodash # Add dev package
```

### Database Operations

```bash
make db-migrate         # Run database migrations/setup
make db-seed            # Seed database with initial data
make db-shell           # Open MongoDB shell
make db-dump            # Dump database to backup/
```

### Utilities

```bash
make update             # Update all dependencies
make clean              # Remove build artifacts
make clean-all          # Full cleanup including volumes
make install-hooks      # Install git hooks
```

## How It Works

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Host Machine                          │
│  (Only Docker + Make installed)                             │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│   Backend     │    │   Frontend    │    │   MongoDB     │
│   Container   │    │   Container   │    │   Container   │
│               │    │               │    │               │
│  • Python 3.12│    │  • Node 22    │    │  • MongoDB 7  │
│  • uv         │    │  • pnpm       │    │               │
│  • FastAPI    │    │  • Vite       │    │               │
│  • Celery     │    │  • React 19   │    │               │
└───────────────┘    └───────────────┘    └───────────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              │
                    ┌───────────────┐
                    │  Redis        │
                    │  Container    │
                    └───────────────┘
```

### Volume Mounts

The development environment uses these volume mounts:

- **Source code**: `./backend:/app/backend`, `./frontend:/app/frontend`
- **Virtual environments**: Named volumes for `node_modules` and `.venv` (persisted between restarts)
- **Database data**: Named volume for MongoDB data

### Hot Reload

Both backend and frontend support hot reload:

- **Backend**: FastAPI dev server with `--reload`
- **Frontend**: Vite dev server with HMR
- **Docker Compose Watch**: Syncs file changes automatically

## Troubleshooting

### Port Conflicts

If ports are already in use:

```bash
# Check what's using the port
lsof -i :8000  # or :5173, :27017, :6379

# Kill the process or change ports in docker-compose.override.yml
```

### Permission Issues

If you encounter permission errors with mounted volumes:

```bash
# Fix ownership
sudo chown -R $(id -u):$(id -g) .

# Or use Docker user namespace remapping
```

### Container Not Starting

```bash
# Check logs
make logs

# Rebuild containers
make down
make rebuild
make up
```

### Clean Slate

```bash
# Complete reset
make down-volumes
make clean-all
make build
make up
```

## Customization

### Adding New Services

Edit `docker-compose.override.yml` to add development services.

### Environment Variables

Create a `.env` file (copied from `.env.example`) to configure:

- `SECRET_KEY` - Application secret
- `FIRST_SUPERUSER` / `FIRST_SUPERUSER_PASSWORD` - Initial admin user
- `MONGODB_URL` - Database connection (default: mongodb://mongodb:27017)
- `REDIS_URL` - Redis connection (default: redis://redis:6379/0)

### Using Different Ports

Edit `docker-compose.override.yml` and change the port mappings:

```yaml
ports:
  - "8080:8000"  # Host:Container
```

## CI/CD Integration

The same commands work in CI/CD:

```yaml
# GitHub Actions example
- name: Run tests
  run: |
    make build
    make up
    make test
```

## Comparison: Local vs Docker Development

| Aspect | Local Development | Docker Development |
|--------|------------------|-------------------|
| Prerequisites | Python, Node, uv, pnpm | Docker, Make |
| Environment consistency | Varies by machine | Identical everywhere |
| Onboarding time | 30+ minutes | 5 minutes |
| Isolation | Shared system | Complete isolation |
| Cleanup | Difficult | `make clean-all` |
| CI/CD parity | Manual setup | Same environment |

## Migration from Local Development

If you're currently using local development:

1. **Backup**: Commit or stash your changes
2. **Stop local services**: Kill any running local servers
3. **Switch to Docker**:
   ```bash
   make down-volumes  # Clean up any existing containers
   make build
   make dev
   ```
4. **Verify**: Open http://localhost:5173

No changes to your code are required!
