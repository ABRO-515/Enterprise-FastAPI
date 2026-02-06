from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db_session
from app.api.v1.controllers.user_controller import UserController
from app.mediators.user_mediator import UserMediator
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth_schema import Role
from app.schemas.user_schema import UserRead, UserUpdate, UserUpdateResponse, UserDeleteResponse
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


def get_user_controller(session: AsyncSession = Depends(get_db_session)) -> UserController:
    repository = UserRepository(session)
    service = UserService(repository)
    mediator = UserMediator(service)
    return UserController(mediator)


@router.put("/{user_id}", response_model=UserUpdateResponse)
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    controller: UserController = Depends(get_user_controller)
) -> UserUpdateResponse:
    return await controller.update_user(user_id, user_update, current_user)


@router.delete("/{user_id}", response_model=UserDeleteResponse)
async def delete_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    controller: UserController = Depends(get_user_controller)
) -> UserDeleteResponse:
    return await controller.delete_user(user_id, current_user)


@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: str, controller: UserController = Depends(get_user_controller)
) -> UserRead:
    return await controller.get_user(user_id)


@router.get("", response_model=list[UserRead])
async def list_users(controller: UserController = Depends(get_user_controller)) -> list[UserRead]:
    return await controller.list_users()
