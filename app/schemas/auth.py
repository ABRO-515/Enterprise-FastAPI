from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class Role(str, Enum):
    admin = "admin"
    user = "user"


class AuthRegister(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    role: Role


class AuthLogin(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=1, max_length=128)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AuthUserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    email: str
    role: Role
    is_active: bool
    created_at: datetime
