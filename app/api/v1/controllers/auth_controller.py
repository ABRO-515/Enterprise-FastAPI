from app.mediators.auth_mediator import AuthMediator
from app.models.user import User
from app.schemas.auth_schema import AuthLogin, AuthRegister, AuthUserRead, LoginResponse


class AuthController:
    def __init__(self, mediator: AuthMediator) -> None:
        self.mediator = mediator

    async def register(self, payload: AuthRegister) -> AuthUserRead:
        user = await self.mediator.register(payload)
        return AuthUserRead(
            id=str(user.id),
            full_name=user.full_name,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at
        )

    async def login(self, payload: AuthLogin) -> LoginResponse:
        return await self.mediator.login(payload)

    async def get_me(self, current_user: User) -> AuthUserRead:
        return AuthUserRead(
            id=str(current_user.id),
            full_name=current_user.full_name,
            email=current_user.email,
            role=current_user.role,
            is_active=current_user.is_active,
            created_at=current_user.created_at
        )
