import uuid
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.iam.auth.jwt import decode_access_token
from app.iam.identity.models import User, Role

bearer_scheme = HTTPBearer()


class CurrentUser:
    """Injected into route handlers via Depends — carries user + permission set."""
    def __init__(self, user: User, permissions: set[str], session_id: uuid.UUID):
        self.user = user
        self.permissions = permissions
        self.session_id = session_id

    def has_permission(self, perm: str) -> bool:
        return perm in self.permissions


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> CurrentUser:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = uuid.UUID(payload["sub"])
        session_id = uuid.UUID(payload.get("jti", str(uuid.uuid4())))
        permissions: set[str] = set(payload.get("permissions", []))
    except (JWTError, ValueError, KeyError):
        raise credentials_exception

    result = await db.execute(
        select(User)
        .options(selectinload(User.roles).selectinload(Role.permissions))
        .where(User.id == user_id, User.deleted_at.is_(None), User.is_active == True)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise credentials_exception

    return CurrentUser(user=user, permissions=permissions, session_id=session_id)


def require_permission(permission: str):
    """Route-level permission guard: Depends(require_permission('sql:execute'))"""
    async def _check(current: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not current.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: '{permission}' required",
            )
        return current
    return _check


def require_verified(current: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if not current.user.is_verified:
        raise HTTPException(status_code=403, detail="Email not verified")
    return current
