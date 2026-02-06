from __future__ import annotations

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

import jwt

from app.core.config import settings
from app.core.errors import UnauthorizedError
from app.db.session import get_db_session
from app.repositories.user_repository import UserRepository

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_db_session),
):
    if not credentials or credentials.scheme.lower() != "bearer":
        raise UnauthorizedError(message="Missing bearer token")

    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise UnauthorizedError(message="Invalid token", details=str(exc)) from exc

    subject = payload.get("sub")
    if not subject:
        raise UnauthorizedError(message="Invalid token subject")

    user_id = str(subject)

    repository = UserRepository(session)
    user = await repository.get_by_id(user_id)
    if not user or not user.is_active:
        raise UnauthorizedError(message="Invalid credentials")

    return user
