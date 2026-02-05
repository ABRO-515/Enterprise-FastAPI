from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.mediators.user_mediator import UserMediator
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserRead
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


def get_user_mediator(session: AsyncSession = Depends(get_db_session)) -> UserMediator:
    repository = UserRepository(session)
    service = UserService(repository)
    return UserMediator(service)


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    mediator: UserMediator = Depends(get_user_mediator),
) -> UserRead:
    return await mediator.create_user(payload)


@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: int, mediator: UserMediator = Depends(get_user_mediator)
) -> UserRead:
    return await mediator.get_user(user_id)


@router.get("", response_model=list[UserRead])
async def list_users(mediator: UserMediator = Depends(get_user_mediator)) -> list[UserRead]:
    return await mediator.list_users()
