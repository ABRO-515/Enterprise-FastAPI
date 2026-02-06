from typing import Any

from app.models.user import User
from app.repositories.user_repository import UserRepository


class UserService:
    def __init__(self, repository: UserRepository) -> None:
        self.repository = repository

    async def get_user(self, user_id: str) -> User:
        user = await self.repository.get_by_id(user_id)
        if not user:
            raise NotFoundError(message="User not found")
        return user

    async def list_users(self) -> list[User]:
        return await self.repository.list()

    async def update_user(self, user_id: str, updates: dict[str, Any]) -> User:
        user = await self.repository.update(user_id, updates)
        if not user:
            raise NotFoundError(message="User not found")
        return user

    async def delete_user(self, user_id: str) -> bool:
        return await self.repository.delete(user_id)
