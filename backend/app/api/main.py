from fastapi import APIRouter

from app.api.routes import items, private, users, utils
from app.api.routes import (
    agents,
    analyses,
    articles,
    drafts,
    external_references,
    llm_model_configs,
    rubrics,
    skills,
    sources,
    submit,
    system_config,
    task_runs,
    token_usage,
    tools,
    workflows,
)
from app.core.config import settings
from app.core.users import auth_backend, fastapi_users
from app.models import UserCreate, UserRead, UserUpdate

api_router = APIRouter()

# fastapi-users auth routes
api_router.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth/jwt",
    tags=["auth"],
)
api_router.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)
api_router.include_router(
    fastapi_users.get_reset_password_router(),
    prefix="/auth",
    tags=["auth"],
)
api_router.include_router(
    fastapi_users.get_verify_router(UserRead),
    prefix="/auth",
    tags=["auth"],
)

# Custom admin/password routes first so /me/* paths take priority over /{id}
api_router.include_router(users.router)

# fastapi-users /users/me, /users/{id} routes
api_router.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)

api_router.include_router(utils.router)
api_router.include_router(items.router)

# Content Intelligence Engine routes
api_router.include_router(sources.router)
api_router.include_router(articles.router)
api_router.include_router(submit.router)
api_router.include_router(analyses.router)
api_router.include_router(agents.router)
api_router.include_router(workflows.router)
api_router.include_router(drafts.router)
api_router.include_router(system_config.router)
api_router.include_router(llm_model_configs.router)
api_router.include_router(skills.router)
api_router.include_router(tools.router)
api_router.include_router(task_runs.router)
api_router.include_router(rubrics.router)
api_router.include_router(external_references.router)
api_router.include_router(token_usage.router)

if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)
