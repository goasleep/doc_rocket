from fastapi import APIRouter

from app.api.routes import items, private, users, utils
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

if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)
