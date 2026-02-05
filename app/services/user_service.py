from app.core.errors import ConflictError, NotFoundError
from app.models.user import User
from app.repositories.user_repository import UserRepository


class UserService:
    def __init__(self, repository: UserRepository) -> None:
        self.repository = repository

    async def create_user(self, name: str, email: str) -> User:
        existing = await self.repository.get_by_email(email)
        if existing:
            raise ConflictError(message="User with this email already exists")
        return await self.repository.create(name=name, email=email)

    async def get_user(self, user_id: int) -> User:
        user = await self.repository.get_by_id(user_id)
        if not user:
            raise NotFoundError(message="User not found")
        return user

    async def list_users(self) -> list[User]:
        return await self.repository.list()
