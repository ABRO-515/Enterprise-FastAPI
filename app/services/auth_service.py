from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.errors import ConflictError, UnauthorizedError
from app.models.auth_user import AuthUser
from app.repositories.auth_user_repository import AuthUserRepository

pwd_context = CryptContext(
    schemes=["pbkdf2_sha256", "bcrypt_sha256", "bcrypt"],
    default="pbkdf2_sha256",
    deprecated="auto",
)


class AuthService:
    def __init__(self, repository: AuthUserRepository) -> None:
        self.repository = repository

    def hash_password(self, password: str) -> str:
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    def create_access_token(self, subject: str) -> str:
        expires = datetime.now(timezone.utc) + timedelta(
            minutes=settings.jwt_access_token_expires_minutes
        )
        payload = {
            "sub": subject,
            "exp": expires,
            "iat": datetime.now(timezone.utc),
        }
        return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    async def register(
        self,
        username: str,
        email: str,
        password: str,
        role: AuthUser.Role,
    ) -> AuthUser:
        existing_username = await self.repository.get_by_username(username)
        if existing_username:
            raise ConflictError(message="Username already exists")

        existing_email = await self.repository.get_by_email(email)
        if existing_email:
            raise ConflictError(message="Email already exists")

        hashed_password = self.hash_password(password)
        return await self.repository.create(
            username=username,
            email=email,
            hashed_password=hashed_password,
            role=role,
        )

    async def authenticate(self, username: str, password: str) -> AuthUser:
        user = await self.repository.get_by_username(username)
        if not user:
            raise UnauthorizedError(message="Invalid credentials")
        if not user.is_active:
            raise UnauthorizedError(message="User is inactive")
        if not self.verify_password(password, user.hashed_password):
            raise UnauthorizedError(message="Invalid credentials")
        return user
