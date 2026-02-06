from __future__ import annotations

from app.models.user import User
from app.schemas.auth import AuthLogin, AuthRegister, Token, LoginResponse
from app.services.auth_service import AuthService


class AuthMediator:
    def __init__(self, service: AuthService) -> None:
        self.service = service

    async def register(self, payload: AuthRegister) -> User:
        role = User.Role(payload.role.value)
        return await self.service.register(
            full_name=payload.full_name,
            email=payload.email,
            password=payload.password,
            role=role,
        )


    async def login(self, payload: AuthLogin) -> LoginResponse:
        user = await self.service.authenticate(email=payload.email, password=payload.password)
        access_token = self.service.create_access_token(subject=str(user.id))
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            id=user.id,
            full_name=user.full_name,
            email=user.email,
            role=user.role,
        )
