from __future__ import annotations

from typing import Any, Self
from dataclasses import asdict, dataclass
from contextlib import suppress

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import cache, CacheBackend  # assume you have proper typing
from app.models.user import User


@dataclass(frozen=True, slots=True)
class CachedUser:
    """Flat, serializable version of user for cache"""
    id: str
    full_name: str
    email: str
    role: str          # or use enum value
    # IMPORTANT: do NOT cache sensitive fields like hashed_password!
    # created_at, updated_at, is_active, etc. — only what you really need

    @classmethod
    def from_orm(cls, user: User) -> Self:
        return cls(
            id=user.id,
            full_name=user.full_name,
            email=user.email,
            role=user.role.value if hasattr(user.role, 'value') else user.role,
        )

    def to_user(self) -> User:
        """Only used in rare cases — prefer passing CachedUser around when possible"""
        return User(
            id=self.id,
            full_name=self.full_name,
            email=self.email,
            role=self.role,
            # IMPORTANT: do NOT reconstruct hashed_password or other sensitive/internal fields
        )


class UserRepository:
    """
    Responsibilities:
    - CRUD for users
    - Read-through caching for hot paths (get by id, get by email)
    - Proper cache invalidation on write
    """

    CACHE_TTL = 300          # move to config or env
    CACHE_KEY_PREFIX = "user"

    def __init__(self, session: AsyncSession, cache_backend: CacheBackend = cache):
        self.session = session
        self.cache = cache_backend

    def _user_key(self, user_id: str) -> str:
        return f"{self.CACHE_KEY_PREFIX}:{user_id}"

    def _email_key(self, email: str) -> str:
        return f"{self.CACHE_KEY_PREFIX}:email:{email.lower()}"

    async def get_by_id(self, user_id: str) -> User | None:
        key = self._user_key(user_id)

        # Cache hit
        cached = await self.cache.get(key)
        if cached is not None:
            try:
                return CachedUser(**cached).to_user()
            except (TypeError, KeyError):
                await self.cache.delete(key)   # corrupt cache → remove
                # continue to DB

        # Cache miss → DB
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if user:
            await self._cache_user(user)

        return user

    async def get_by_email(self, email: str) -> User | None:
        key = self._email_key(email)

        cached = await self.cache.get(key)
        if cached is not None:
            try:
                return CachedUser(**cached).to_user()
            except (TypeError, KeyError):
                await self.cache.delete(key)

        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()

        if user:
            await self._cache_user(user)
            # Also cache by email
            await self.cache.set(key, asdict(CachedUser.from_orm(user)), ttl=self.CACHE_TTL)

        return user

    async def _cache_user(self, user: User) -> None:
        """Central place to cache a user (used by both get_by_id and get_by_email)"""
        if not user.id:
            return

        cu = CachedUser.from_orm(user)
        data = asdict(cu)

        await self.cache.set(
            self._user_key(user.id),
            data,
            ttl=self.CACHE_TTL
        )

        # Also cache by email (write-through style for email lookups)
        if user.email:
            await self.cache.set(
                self._email_key(user.email),
                data,
                ttl=self.CACHE_TTL
            )

    async def create(
        self,
        full_name: str,
        email: str,
        hashed_password: str,
        role: User.Role = User.Role.user,
    ) -> User:
        user = User(
            full_name=full_name,
            email=email.lower(),           # normalize early
            hashed_password=hashed_password,
            role=role,
        )

        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)

        await self._invalidate_user_caches(user)

        return user

    async def _invalidate_user_caches(self, user: User) -> None:
        """Called after every write operation"""
        if user.id:
            await self.cache.delete(self._user_key(user.id))

        if user.email:
            await self.cache.delete(self._email_key(user.email))

    async def update(self, user_id: str, updates: dict[str, Any]) -> User:
        user = await self.get_by_id(user_id)
        if not user:
            return None  # or raise

        # Check email uniqueness if email is being updated
        if 'email' in updates:
            existing = await self.get_by_email(updates['email'])
            if existing and existing.id != user_id:
                raise ValueError("Email already in use")

        for key, value in updates.items():
            if hasattr(user, key):
                setattr(user, key, value)

        await self.session.commit()
        await self.session.refresh(user)
        await self._invalidate_user_caches(user)

        return user

    async def list(self) -> list[User]:
        result = await self.session.execute(select(User))
        return result.scalars().all()

    async def delete(self, user_id: str) -> bool:
        user = await self.get_by_id(user_id)
        if not user:
            return False
        await self.session.delete(user)
        await self.session.commit()
        await self._invalidate_user_caches(user)
        return True