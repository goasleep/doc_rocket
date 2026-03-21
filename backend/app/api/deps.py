from typing import Annotated

from fastapi import Depends

from app.core.users import current_active_user, current_superuser
from app.models import User

CurrentUser = Annotated[User, Depends(current_active_user)]

SuperuserDep = Annotated[User, Depends(current_superuser)]


def get_current_active_superuser(current_user: SuperuserDep) -> User:
    # fastapi_users.current_user(superuser=True) already validates superuser status
    return current_user
