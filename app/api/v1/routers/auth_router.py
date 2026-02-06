from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db_session
from app.api.v1.controllers.auth_controller import AuthController
from app.mediators.auth_mediator import AuthMediator
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth_schema import AuthLogin, AuthRegister, AuthUserRead, LoginResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_controller(session: AsyncSession = Depends(get_db_session)) -> AuthController:
    repository = UserRepository(session)
    service = AuthService(repository)
    mediator = AuthMediator(service)
    return AuthController(mediator)


@router.post("/register", response_model=AuthUserRead, status_code=status.HTTP_201_CREATED)
async def register(
    payload: AuthRegister,
    controller: AuthController = Depends(get_auth_controller),
) -> AuthUserRead:
    return await controller.register(payload)


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: AuthLogin,
    controller: AuthController = Depends(get_auth_controller),
) -> LoginResponse:
    return await controller.login(payload)


@router.get("/me", response_model=AuthUserRead)
async def me(
    current_user: User = Depends(get_current_user),
    controller: AuthController = Depends(get_auth_controller),
) -> AuthUserRead:
    return controller.get_me(current_user)
