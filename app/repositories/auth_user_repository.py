from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth_user import AuthUser


class AuthUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: str) -> AuthUser | None:
        result = await self.session.execute(select(AuthUser).where(AuthUser.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> AuthUser | None:
        result = await self.session.execute(select(AuthUser).where(AuthUser.username == username))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> AuthUser | None:
        result = await self.session.execute(select(AuthUser).where(AuthUser.email == email))
        return result.scalar_one_or_none()

    async def create(
        self,
        username: str,
        email: str,
        hashed_password: str,
        role: AuthUser.Role,
    ) -> AuthUser:
        user = AuthUser(username=username, email=email, hashed_password=hashed_password, role=role)
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user
