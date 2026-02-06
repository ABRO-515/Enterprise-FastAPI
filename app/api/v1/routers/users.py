from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.core.errors import ForbiddenError, NotFoundError
from app.db.session import get_db_session
from app.mediators.user_mediator import UserMediator
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import Role
from app.schemas.user import UserRead, UserUpdate, UserUpdateResponse, UserDeleteResponse
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


def get_user_mediator(session: AsyncSession = Depends(get_db_session)) -> UserMediator:
    repository = UserRepository(session)
    service = UserService(repository)
    return UserMediator(service)

    # here create a route of user update. Basically the users that are in Users table


@router.put("/{user_id}", response_model=UserUpdateResponse)
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    mediator: UserMediator = Depends(get_user_mediator)
) -> UserUpdateResponse:
    if current_user.id != user_id and current_user.role != Role.admin:
        raise ForbiddenError(message="Unable to change")
    updates = user_update.model_dump(exclude_unset=True)
    user = await mediator.update_user(user_id, updates)
    return UserUpdateResponse(
        message="Successfully updated user details",
        user=UserRead.model_validate(user)
    )


@router.delete("/{user_id}", response_model=UserDeleteResponse)
async def delete_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    mediator: UserMediator = Depends(get_user_mediator)
) -> UserDeleteResponse:
    if current_user.id != user_id and current_user.role != Role.admin:
        raise ForbiddenError(message="Unable to delete")
    success = await mediator.delete_user(user_id)
    if not success:
        raise NotFoundError(message="User not found")
    return UserDeleteResponse(message="User deleted successfully")


@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: str, mediator: UserMediator = Depends(get_user_mediator)
) -> UserRead:
    return await mediator.get_user(user_id)


@router.get("", response_model=list[UserRead])
async def list_users(mediator: UserMediator = Depends(get_user_mediator)) -> list[UserRead]:
    return await mediator.list_users()
