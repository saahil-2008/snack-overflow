# app/core/auth.py — JWT auth + role guard (required, copy as-is; uses PyJWT)
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.errors import ApiError

JWT_SECRET = os.environ.get("JWT_SECRET", "dev-only-change-me-at-least-32chars!")
JWT_ALGORITHM = "HS256"
JWT_TTL = timedelta(hours=24)
_bearer = HTTPBearer(auto_error=False)  # auto_error=False: we emit our own 401 envelope


@dataclass(frozen=True)
class CurrentUser:
    user_id: UUID
    role: str


def issue_token(user_id: UUID, role: str) -> tuple[str, datetime]:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    exp = now + JWT_TTL
    claims = {"sub": str(user_id), "userId": str(user_id), "role": role, "iat": int(now.timestamp()), "exp": int(exp.timestamp())}
    return jwt.encode(claims, JWT_SECRET, algorithm=JWT_ALGORITHM), exp


def current_user(creds: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> CurrentUser:
    if creds is None or creds.scheme.lower() != "bearer":
        raise ApiError(401, "AUTH_REQUIRED", "Login required")
    try:
        claims = jwt.decode(creds.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return CurrentUser(user_id=UUID(claims["userId"]), role=claims["role"])
    except jwt.ExpiredSignatureError:
        raise ApiError(401, "TOKEN_EXPIRED", "Session expired, please log in again")
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise ApiError(401, "TOKEN_INVALID", "Invalid token")


def require_roles(*roles: str):
    def _dep(user: CurrentUser = Depends(current_user)) -> CurrentUser:
        if user.role not in roles:
            raise ApiError(403, "FORBIDDEN_ROLE", "Your role cannot perform this action",
                           {"requiredRoles": list(roles), "yourRole": user.role})
        return user
    return _dep
