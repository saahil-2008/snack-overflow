# app/routers/users.py — GET /users/me, PATCH /users/me (Section 4.2)
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, current_user
from app.core.errors import ApiError
from app.db.models import UserRow
from app.db.session import get_db
from app.schemas import ApiSuccess, UpdateProfileRequest, User

router = APIRouter(prefix="/api/v1/users", tags=["users"])


def _user_dto(row: UserRow) -> User:
    return User.model_validate(row, from_attributes=True)


@router.get("/me", status_code=200, response_model=ApiSuccess[User])
def get_me(user: CurrentUser = Depends(current_user), db: Session = Depends(get_db)):
    row = db.query(UserRow).filter(UserRow.id == user.user_id).first()
    if not row:
        raise ApiError(404, "NOT_FOUND", "User not found", {"resource": "user", "id": str(user.user_id)})
    return ApiSuccess(data=_user_dto(row))


@router.patch("/me", status_code=200, response_model=ApiSuccess[User])
def update_me(body: UpdateProfileRequest, user: CurrentUser = Depends(current_user),
              db: Session = Depends(get_db)):
    row = db.query(UserRow).filter(UserRow.id == user.user_id).first()
    if not row:
        raise ApiError(404, "NOT_FOUND", "User not found", {"resource": "user", "id": str(user.user_id)})

    updates = body.model_dump(by_alias=False, exclude_unset=True)
    for k, v in updates.items():
        setattr(row, k, v)

    db.commit()
    db.refresh(row)
    return ApiSuccess(data=_user_dto(row))
