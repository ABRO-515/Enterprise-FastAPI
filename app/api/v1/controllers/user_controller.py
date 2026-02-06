from app.core.errors import ForbiddenError, NotFoundError
from app.mediators.user_mediator import UserMediator
from app.models.user import User
from app.schemas.auth_schema import Role
from app.schemas.user_schema import UserDeleteResponse, UserRead, UserUpdate, UserUpdateResponse


class UserController:
    def __init__(self, mediator: UserMediator) -> None:
        self.mediator = mediator

    async def update_user(self, user_id: str, user_update: UserUpdate, current_user: User) -> UserUpdateResponse:
        if current_user.id != user_id and current_user.role != Role.admin:
            raise ForbiddenError(message="Unable to change")
        updates = user_update.model_dump(exclude_unset=True)
        user = await self.mediator.update_user(user_id, updates)
        return UserUpdateResponse(
            message="Successfully updated user details",
            user=UserRead.model_validate(user)
        )

    async def delete_user(self, user_id: str, current_user: User) -> UserDeleteResponse:
        if current_user.id != user_id and current_user.role != Role.admin:
            raise ForbiddenError(message="Unable to delete")
        success = await self.mediator.delete_user(user_id)
        if not success:
            raise NotFoundError(message="User not found")
        return UserDeleteResponse(message="User deleted successfully")

    async def get_user(self, user_id: str) -> UserRead:
        return await self.mediator.get_user(user_id)

    async def list_users(self) -> list[UserRead]:
        return await self.mediator.list_users()
