from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db_session
from app.mediators.auth_mediator import AuthMediator
from app.models.auth_user import AuthUser
from app.repositories.auth_user_repository import AuthUserRepository
from app.schemas.auth import AuthLogin, AuthRegister, AuthUserRead, Token
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_mediator(session: AsyncSession = Depends(get_db_session)) -> AuthMediator:
    repository = AuthUserRepository(session)
    service = AuthService(repository)
    return AuthMediator(service)


@router.post("/register", response_model=AuthUserRead, status_code=status.HTTP_201_CREATED)
async def register(
    payload: AuthRegister,
    mediator: AuthMediator = Depends(get_auth_mediator),
) -> AuthUserRead:
    return await mediator.register(payload)


@router.post("/login", response_model=Token)
async def login(
    payload: AuthLogin,
    mediator: AuthMediator = Depends(get_auth_mediator),
) -> Token:
    return await mediator.login(payload)


@router.get("/me", response_model=AuthUserRead)
async def me(current_user: AuthUser = Depends(get_current_user)) -> AuthUserRead:
    return current_user
