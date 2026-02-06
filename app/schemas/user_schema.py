from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.auth_schema import Role


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    full_name: str
    email: str
    role: Role
    is_active: bool
    created_at: datetime


class UserUpdate(BaseModel):
    full_name: str | None = None
    email: str | None = None
    role: Role | None = None
    is_active: bool | None = None


class UserUpdateResponse(BaseModel):
    message: str
    user: UserRead


class UserDeleteResponse(BaseModel):
    message: str
