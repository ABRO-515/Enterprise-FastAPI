from app.models.user import User
from app.schemas.user import UserCreate
from app.services.user_service import UserService


class UserMediator:
    def __init__(self, service: UserService) -> None:
        self.service = service

    async def create_user(self, payload: UserCreate) -> User:
        return await self.service.create_user(name=payload.name, email=payload.email)

    async def get_user(self, user_id: int) -> User:
        return await self.service.get_user(user_id)

    async def list_users(self) -> list[User]:
        return await self.service.list_users()
