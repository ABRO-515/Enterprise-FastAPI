from __future__ import annotations
from typing import Any

from app.schemas.user_schema import UserRead
from app.services.user_service import UserService


class UserMediator:
    def __init__(self, service: UserService) -> None:
        self.service = service

    async def get_user(self, user_id: str) -> UserRead:
        user = await self.service.get_user(user_id)
        return UserRead.model_validate(user)

    async def list_users(self) -> list[UserRead]:
        users = await self.service.list_users()
        return [UserRead.model_validate(user) for user in users]

    async def update_user(self, user_id: str, updates: dict[str, Any]) -> User:
        return await self.service.update_user(user_id, updates)

    async def delete_user(self, user_id: str) -> bool:
        return await self.service.delete_user(user_id)
