from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional

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

# class UserResponseModel(BaseModel):
#     id: int
#     email: EmailStr
#     role: str
#     fullName: str
#     isActive: bool

#     class Config:
#         from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserLogin(BaseModel):
    email: str
    password: str

class ForgotPasswordSchema(BaseModel):
    email: EmailStr


class ResetPasswordSchema(BaseModel):
    token: str
    password: str
    confirmPassword: str

class ChangePasswordByAdminSchema(BaseModel):
    password: str
    confirmPassword: str

class UserResponseModel(BaseModel):
    id: int
    fullName: str
    email: str
    isActive: bool
    isVerified: bool
    role: Optional[str] = None     

class passwordChangeDefault(BaseModel):
        password: str
        confirmPassword: str