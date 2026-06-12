from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError
from sqlmodel import select
from utils.database import get_database
from utils.jwt_helper import ALGORITHM, SECRET_KEY
from user.model import User


def get_current_user(
    request: Request,
    db: Session = Depends(get_database)
):
    try:
        auth_header = request.headers.get("authorization")

        if not auth_header:
            raise HTTPException(status_code=401, detail="No token")

        # Expect: "Bearer <token>"
        token = auth_header.split(" ")[-1]

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        user_id = payload.get("id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")

        user = db.exec(select(User).where(User.id == user_id)).first()

        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        return user

    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")