# app/routers/auth.py — register & login (Section 4.2)
from datetime import datetime, timezone
from uuid import uuid4

import bcrypt
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import issue_token
from app.core.errors import ApiError
from app.db.models import UserRow
from app.db.session import get_db
from app.schemas import (
    ApiSuccess, AuthResponse, LoginRequest, RegisterRequest, User,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _hash_pw(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def _verify_pw(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def _user_dto(row: UserRow) -> User:
    return User.model_validate(row, from_attributes=True)


@router.post("/register", status_code=201, response_model=ApiSuccess[AuthResponse])
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(UserRow).filter(UserRow.phone == body.phone).first()
    if existing:
        raise ApiError(409, "PHONE_ALREADY_REGISTERED",
                       "This phone number is already registered",
                       {"phone": body.phone})

    user_id = uuid4()
    now = datetime.now(timezone.utc)
    row = UserRow(
        id=user_id,
        name=body.name,
        phone=body.phone,
        password_hash=_hash_pw(body.password),
        role=body.role,
        language=body.language,
        theme="SYSTEM",
        organization_name=body.organization_name,
        home_latitude=None,
        home_longitude=None,
        created_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    token, exp = issue_token(user_id, body.role)
    return ApiSuccess(data=AuthResponse(
        access_token=token,
        expires_at=exp,
        user=_user_dto(row),
    ))


@router.post("/login", status_code=200, response_model=ApiSuccess[AuthResponse])
def login(body: LoginRequest, db: Session = Depends(get_db)):
    row = db.query(UserRow).filter(UserRow.phone == body.phone).first()
    if not row or not _verify_pw(body.password, row.password_hash):
        raise ApiError(401, "INVALID_CREDENTIALS", "Invalid phone number or password")

    token, exp = issue_token(row.id, row.role)
    return ApiSuccess(data=AuthResponse(
        access_token=token,
        expires_at=exp,
        user=_user_dto(row),
    ))
