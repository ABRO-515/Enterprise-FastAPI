from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db_session
from app.mediators.auth_mediator import AuthMediator
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import AuthLogin, AuthRegister, AuthUserRead, LoginResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_mediator(session: AsyncSession = Depends(get_db_session)) -> AuthMediator:
    repository = UserRepository(session)
    service = AuthService(repository)
    return AuthMediator(service)


@router.post("/register", response_model=AuthUserRead, status_code=status.HTTP_201_CREATED)
async def register(
    payload: AuthRegister,
    mediator: AuthMediator = Depends(get_auth_mediator),
) -> AuthUserRead:
    return await mediator.register(payload)


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: AuthLogin,
    mediator: AuthMediator = Depends(get_auth_mediator),
) -> LoginResponse:
    return await mediator.login(payload)


@router.get("/me", response_model=AuthUserRead)
async def me(current_user: User = Depends(get_current_user)) -> AuthUserRead:
    return current_user
