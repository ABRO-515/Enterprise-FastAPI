from app.models.auth_user import AuthUser
from app.schemas.auth import AuthLogin, AuthRegister, Token
from app.services.auth_service import AuthService


class AuthMediator:
    def __init__(self, service: AuthService) -> None:
        self.service = service

    async def register(self, payload: AuthRegister) -> AuthUser:
        role = AuthUser.Role(payload.role.value)
        return await self.service.register(
            username=payload.username,
            email=payload.email,
            password=payload.password,
            role=role,
        )

    async def login(self, payload: AuthLogin) -> Token:
        user = await self.service.authenticate(username=payload.username, password=payload.password)
        access_token = self.service.create_access_token(subject=str(user.id))
        return Token(access_token=access_token)
