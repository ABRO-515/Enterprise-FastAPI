from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.errors import ConflictError, UnauthorizedError
from app.models.user import User
from app.repositories.user_repository import UserRepository

pwd_context = CryptContext(
    schemes=["pbkdf2_sha256", "bcrypt_sha256", "bcrypt"],
    default="pbkdf2_sha256",
    deprecated="auto",
)


class AuthService:
    """Authentication actions that rely on the unified `User` model."""

    def __init__(self, repository: UserRepository) -> None:
        self.repository = repository

    # ------------------------------------------------------------------
    # Password helpers
    # ------------------------------------------------------------------
    @staticmethod
    def hash_password(password: str) -> str:
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    # ------------------------------------------------------------------
    # JWT helpers
    # ------------------------------------------------------------------
    @staticmethod
    def create_access_token(subject: str) -> str:
        now = datetime.now(timezone.utc)
        expires = now + timedelta(minutes=settings.jwt_access_token_expires_minutes)

        payload = {
            "sub": subject,
            "iat": now,
            "exp": expires,
        }

        return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def register(
        self,
        full_name: str,
        email: str,
        password: str,
        role: User.Role = User.Role.user,
    ) -> User:
        """Register a new user if the email is not taken."""
        existing_user = await self.repository.get_by_email(email)
        if existing_user:
            raise ConflictError(message="Email already exists")

        hashed_password = self.hash_password(password)
        return await self.repository.create(
            full_name=full_name,
            email=email,
            hashed_password=hashed_password,
            role=role,
        )

    async def authenticate(self, email: str, password: str) -> User:
        """Validate credentials and return the active user."""
        user = await self.repository.get_by_email(email)
        if not user or not user.is_active:
            raise UnauthorizedError(message="Invalid credentials")

        if not self.verify_password(password, user.hashed_password):
            raise UnauthorizedError(message="Invalid credentials")

        return user
