from typing import Any

from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.message_broker import publish  # ✅ ADD THIS

from app.core.errors import NotFoundError


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

        # ✅ 🔥 PUBLISH EVENT (TOPIC EXCHANGE)
        await publish(
            routing_key="user.updated",
            message={
                "user_id": str(user.id),
                "updates": updates,
            },
        )

        return user

    async def delete_user(self, user_id: str) -> bool:
        deleted = await self.repository.delete(user_id)

        if deleted:
            # ✅ 🔥 EVENT AFTER SUCCESS
            await publish(
                routing_key="user.deleted",
                message={
                    "user_id": user_id,
                },
            )

        return deleted