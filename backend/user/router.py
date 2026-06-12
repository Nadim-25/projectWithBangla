from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from utils.database import get_database
from user.model import User
from user.schema import passwordChangeDefault, UserResponseModel, CreateUserSchema, UserResponseModel, UserLogin, ChangePasswordSchema, ForgotPasswordSchema, ChangePasswordByAdminSchema
from utils.jwt_helper import hash_password, verify_password
from utils.jwt_helper import ALGORITHM, SECRET_KEY
from jose import jwt
from datetime import datetime, timedelta
from utils.get_current_user import get_current_user


user_router = APIRouter(tags=["Users"])


@user_router.post("/register")
def register(user: CreateUserSchema, session: Session = Depends(get_database)):
    existing = session.exec(
        select(User).where(User.email == user.email)
    ).first()

    if existing:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email Already Registered")
    
    if not user.hashedPassword.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="New Password Can't be Empty"
        )

    if not user.confirmHashedPassword.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Confirm Password can't be Empty"
        )

    if user.hashedPassword != user.confirmHashedPassword:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Passwords Do not Match"
        )

    new_user = User(
        fullName = user.fullName,
        userName = user.userName,
        email=user.email,
        hashedPassword=hash_password(user.hashedPassword)
    )

    session.add(new_user)
    session.commit()
    session.refresh(new_user)

    return {"message": "User Created Successfully"}


@user_router.post("/login")
def login_user(body:UserLogin, db:Session = Depends(get_database)):
    user = db.exec(
        select(User).where(User.email == body.email)
    ).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Wrong Email")
    
    if not user.isActive:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is not active")
    
    if not user.isVerified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is not Verified")
    
    if not verify_password(body.password, user.hashedPassword):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Wrong Password")
    
    from utils.jwt_helper import ACCESS_TOKEN_EXPIRE_MINUTES
    exp_time = datetime.now() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    token = jwt.encode({"id": user.id, "role": user.role, "exp": exp_time.timestamp()}, SECRET_KEY, ALGORITHM)
    
    return {
    "access_token": token,
    "token_type": "bearer"
    }

@user_router.get("/is-auth", response_model = UserResponseModel)
def is_authenticated(current_user: User = Depends(get_current_user)):
    return current_user

@user_router.put("/change-password")
def changePassword(
    body: ChangePasswordSchema,
    db: Session = Depends(get_database),
    current_user: User = Depends(get_current_user),
):

    # =========================
    # USER CHECK
    # =========================
    if not current_user:
        raise HTTPException(
            status_code=401,
            detail="User Not Found"
        )

    # =========================
    # VERIFY OLD PASSWORD
    # =========================
    oldNewMatched = verify_password(
        body.oldPassword,
        current_user.hashedPassword
    )

    if not body.newPassword.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="New password can't be empty"
        )

    if not body.confirmNewPassword.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Confirm password can't be empty"
        )

    if not oldNewMatched:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Existing Password not correct"
        )

    # =========================
    # MATCH NEW PASSWORDS
    # =========================
    if body.newPassword != body.confirmNewPassword:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Passwords do not match"
        )

    # =========================
    # HASH NEW PASSWORD
    # =========================
    hashed_password = hash_password(body.newPassword)

    # =========================
    # UPDATE ONLY PASSWORD FIELD
    # =========================
    current_user.hashedPassword = hashed_password

    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    # =========================
    # RESPONSE
    # =========================
    return {
        "success": True,
        "message": "Password changed successfully"
    }
    


from fastapi_mail import FastMail, MessageSchema

from config.mail import conf

import secrets
from datetime import datetime, timedelta

import os



@user_router.post("/forgot-password")
async def forgot_password(
    body: ForgotPasswordSchema,
    db: Session = Depends(get_database),
):

    # =========================
    # FIND USER
    # =========================
    statement = select(User).where(User.email == body.email)

    user = db.exec(statement).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not found"
        )

    # =========================
    # GENERATE TOKEN
    # =========================
    reset_token = secrets.token_urlsafe(32)

    expiry = datetime.now() + timedelta(minutes=15)

    # =========================
    # SAVE TOKEN
    # =========================
    user.passwordResetToken = reset_token
    user.passwordResetExpiry = expiry

    db.add(user)
    db.commit()

    # =========================
    # RESET URL
    # =========================
    reset_url = (
        f"{os.getenv('FRONTEND_URL')}"
        f"/reset-password?token={reset_token}"
    )

    # =========================
    # EMAIL
    # =========================
    html = f"""
    <h2>Password Reset</h2>

    <p>Click below link to reset password:</p>

    <a href="{reset_url}">
        Reset Password
    </a>

    <p>Link expires in 15 minutes.</p>
    """

    message = MessageSchema(
        subject="Reset Password",
        recipients=[user.email],
        body=html,
        subtype="html",
    )

    fm = FastMail(conf)

    await fm.send_message(message)

    return {
        "success": True,
        "message": "Password reset email sent"
    }

from user.schema import ResetPasswordSchema

from utils.jwt_helper import hash_password


@user_router.post("/reset-password")
def reset_password(
    body: ResetPasswordSchema,
    db: Session = Depends(get_database),
):

    # =========================
    # MATCH PASSWORDS
    # =========================
    if body.password != body.confirmPassword:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Passwords do not match"
        )

    # =========================
    # FIND USER BY TOKEN
    # =========================
    statement = select(User).where(
        User.passwordResetToken == body.token
    )

    user = db.exec(statement).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid token"
        )

    # =========================
    # CHECK EXPIRY
    # =========================
    if (
        not user.passwordResetExpiry
        or user.passwordResetExpiry < datetime.utcnow()
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token expired"
        )

    # =========================
    # HASH PASSWORD
    # =========================
    hashed = hash_password(body.password)

    # =========================
    # UPDATE USER
    # =========================
    user.hashedPassword = hashed

    # clear token
    user.passwordResetToken = None
    user.passwordResetExpiry = None

    db.add(user)
    db.commit()

    return {
        "success": True,
        "message": "Password reset successful"
    }

@user_router.put("/password-change-byadmin/{userId}")
def resetPasswordByAdmin(userId:int, body:ChangePasswordByAdminSchema, session:Session = Depends(get_database), current_user: User = Depends(get_current_user)):
    userRole = current_user.role

    if not userRole == "admin":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="You are not Authorized")
    
    appliedUser = session.exec(
        select(User).where(User.id == userId)
    ).first()

    if not appliedUser:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not exist")
    
    if not body.password.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password can't be empty"
        )

    if not body.confirmPassword.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Confirm password can't be empty"
        )

    if body.password != body.confirmPassword:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Passwords do not match"
        )
    
    appliedUser.hashedPassword = hash_password(body.password)

    session.add(appliedUser)
    session.commit()

    return {
        "success": True,
        "message": "Password Changed successful"
    }


@user_router.get("/all-users", response_model=list[UserResponseModel])
def get_all_users(
    session: Session = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    # ✅ Optional admin check
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access denied"
        )

    # ✅ Correct query
    statement = select(User)

    all_users = session.exec(statement).all()

    return all_users

@user_router.put("/toggle-active/{user_id}")
def toggle_active(
    user_id: int,
    session: Session = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    # admin only
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access denied"
        )

    statement = select(User).where(User.id == user_id)

    user = session.exec(statement).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # toggle
    user.isActive = not user.isActive

    session.add(user)
    session.commit()
    session.refresh(user)

    return {
        "message": "User active status updated",
        "isActive": user.isActive
    }
    

@user_router.put("/toggle-verified/{user_id}")
def toggle_verified(
    user_id: int,
    session: Session = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    # admin only
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access denied"
        )

    statement = select(User).where(User.id == user_id)

    user = session.exec(statement).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # toggle
    user.isVerified = not user.isVerified

    session.add(user)
    session.commit()
    session.refresh(user)

    return {
        "message": "User verified status updated",
        "isVerified": user.isVerified
    }

@user_router.post("/login1")
def login_user(body: UserLogin, db: Session = Depends(get_database)):
    user = db.exec(
        select(User).where(User.email == body.email)
    ).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Wrong CredentialUE")

    if not user.isActive:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is not active")

    if not user.isVerified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is not Verified")

    if not verify_password(body.password, user.hashedPassword):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Wrong CredentialPW")

    from utils.jwt_helper import ACCESS_TOKEN_EXPIRE_MINUTES
    exp_time = datetime.now() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    token = jwt.encode(
        {
            "id": user.id,
            "role": user.role,
            "requiresPasswordChange": user.requiresPasswordChange,
            "exp": exp_time.timestamp(),
        },
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "requiresPasswordChange": user.requiresPasswordChange,  # ✅ direct
        "userId": user.id
    }

@user_router.get("/admin-summary")
def admin_summary(
    session: Session = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    from chatbot.model import Document

    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Access denied")

    all_users = session.exec(select(User)).all()
    all_docs = session.exec(select(Document)).all()

    total_users = len(all_users)
    active_users = sum(1 for u in all_users if u.isActive)
    verified_users = sum(1 for u in all_users if u.isVerified)
    admin_users = sum(1 for u in all_users if u.role == "admin")

    total_docs = len(all_docs)
    processed_docs = sum(1 for d in all_docs if d.processed)

    return {
        "users": {
            "total": total_users,
            "active": active_users,
            "inactive": total_users - active_users,
            "verified": verified_users,
            "unverified": total_users - verified_users,
            "admins": admin_users,
            "regular": total_users - admin_users,
        },
        "documents": {
            "total": total_docs,
            "processed": processed_docs,
            "unprocessed": total_docs - processed_docs,
        },
    }


@user_router.put("/force-change-password")
def force_change_password(
    body: ChangePasswordByAdminSchema,
    db: Session = Depends(get_database),
    current_user: User = Depends(get_current_user)
):

    if not body.password.strip():
        raise HTTPException(
            status_code=400,
            detail="Password required"
        )

    if body.password != body.confirmPassword:
        raise HTTPException(
            status_code=400,
            detail="Passwords do not match"
        )

    # prevent PASSWORD reuse
    if body.password == "PASSWORD":
        raise HTTPException(
            status_code=400,
            detail="Cannot use temporary password"
        )

    current_user.hashedPassword = hash_password(body.password)
    current_user.requiresPasswordChange = False

    db.add(current_user)
    db.commit()

    return {
        "success": True,
        "message": "Password changed successfully"
    }
