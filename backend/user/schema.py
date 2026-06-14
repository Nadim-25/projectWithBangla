from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import datetime

class CreateUserSchema(BaseModel):
    fullName: str
    userName: str
    email: EmailStr
    hashedPassword: str
    confirmHashedPassword: str

    @field_validator("hashedPassword", "confirmHashedPassword")
    @classmethod
    def validate_password(cls, value):
        if not value.strip():
            raise ValueError("Password cannot be empty")
        return value

class ChangePasswordSchema(BaseModel):
    oldPassword: str
    newPassword: str
    confirmNewPassword: str

    @field_validator("newPassword", "confirmNewPassword")
    @classmethod
    def validate_password(cls, value):
        if not value.strip():
            raise ValueError("Password cannot be empty")
        return value
  

class UserRead(BaseModel):
    id: int
    email: EmailStr
    password: str
    role: str
    is_active: bool

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserLogin(BaseModel):
    email: str
    password: str

class ChangePasswordByAdminSchema(BaseModel):
    password: str
    confirmPassword: str

class UserResponseModel(BaseModel):
    id: int
    fullName: str
    userName: str
    email: str
    role: Optional[str] = None
    division: Optional[str] = None
    department: Optional[str] = None
    isActive: bool
    isVerified: bool
    createdAt: Optional[datetime] = None

    class Config:
        from_attributes = True


class UpdateUserSchema(BaseModel):
    fullName: str
    userName: str
    email: str
    role: str
    division: str
    department: str

class passwordChangeDefault(BaseModel):
        password: str
        confirmPassword: str