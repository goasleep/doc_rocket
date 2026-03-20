# Full Stack FastAPI Template

## Technology Stack

- **Backend:** [FastAPI](https://fastapi.tiangolo.com) + [Beanie ODM](https://beanie-odm.dev) + [MongoDB](https://www.mongodb.com)
  - [Pydantic](https://docs.pydantic.dev) for data validation and settings management
  - [PyJWT](https://pyjwt.readthedocs.io) for JWT authentication
  - [pwdlib](https://github.com/frankie567/pwdlib) (argon2 + bcrypt) for password hashing
- **Frontend:** [React](https://react.dev) 19 + TypeScript + [Vite](https://vitejs.dev)
  - [TanStack Router](https://tanstack.com/router) + [TanStack Query](https://tanstack.com/query)
  - [Tailwind CSS v4](https://tailwindcss.com) + [shadcn/ui](https://ui.shadcn.com)
  - Auto-generated TypeScript client from OpenAPI schema
  - [Playwright](https://playwright.dev) for End-to-End testing
  - Dark mode support
- **Infrastructure:** [Docker Compose](https://docs.docker.com/compose) + [Traefik](https://traefik.io) reverse proxy
- **Package managers:** `uv` (Python), `bun` (JS)

## Quick Start

Clone and start:

```bash
git clone <this-repo> my-project
cd my-project
docker compose watch
```

Visit:
- Frontend: http://localhost (or http://localhost:5173 in dev)
- API docs: http://localhost/api/v1/docs

### Configure

Edit `.env` before deploying. At minimum change:

- `SECRET_KEY`
- `FIRST_SUPERUSER_PASSWORD`
- `MONGODB_URL` (for production)

Generate a secret key:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Development

See [development.md](./development.md).

## Deployment

See [deployment.md](./deployment.md).

## License

MIT
