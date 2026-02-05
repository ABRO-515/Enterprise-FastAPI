from __future__ import annotations

from typing import Any
from sqlalchemy.inspection import inspect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import cache
from app.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession, cache_backend=cache) -> None:
        self.session = session
        self._cache = cache_backend

    async def _cache_key(self, user_id: int) -> str:  # noqa: D401
        return f"user:{user_id}"

    def _to_dict(self, user: User) -> dict[str, Any]:  # noqa: D401
        return {c.key: getattr(user, c.key) for c in inspect(user).mapper.column_attrs}

    async def get_by_id(self, user_id: int) -> User | None:
        # try cache first
        cached = await self._cache.get(await self._cache_key(user_id))
        if cached is not None:
            return User(**cached)  # type: ignore[arg-type]

        result = await self.session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user:
            await self._cache.set(await self._cache_key(user.id), self._to_dict(user), ttl=300)
        return user

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def list(self) -> list[User]:
        result = await self.session.execute(select(User).order_by(User.id))
        return list(result.scalars().all())

    async def create(self, name: str, email: str) -> User:
        user = User(name=name, email=email)
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        # Invalidate caches
        await self._cache.delete_pattern("user:*")
        return user
