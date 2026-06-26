import uuid
import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.firebase import get_firebase_app
from app.iam.identity.models import User

logger = logging.getLogger(__name__)
bearer_scheme = HTTPBearer()


class CurrentUser:
    """Injected into route handlers via Depends — carries user + permission set."""

    def __init__(self, user: User, permissions: set[str], session_id: uuid.UUID):
        self.user = user
        self.permissions = permissions
        self.session_id = session_id

    def has_permission(self, perm: str) -> bool:
        return perm in self.permissions


async def _get_or_create_user(
    firebase_uid: str,
    email: str,
    full_name: str,
    db: AsyncSession,
) -> User:
    # 1. Lookup by Firebase UID stored in oauth_id
    result = await db.execute(
        select(User).where(
            User.oauth_id == firebase_uid,
            User.oauth_provider == "firebase",
            User.deleted_at.is_(None),
        )
    )
    user = result.scalar_one_or_none()
    if user:
        return user

    # 2. Lookup by email (links an existing account to Firebase)
    result = await db.execute(
        select(User).where(User.email == email, User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()
    if user:
        user.oauth_id = firebase_uid
        user.oauth_provider = "firebase"
        user.is_verified = True
        await db.flush()
        return user

    # 3. Create a new user record for this Firebase identity
    user = User(
        email=email,
        full_name=full_name or email.split("@")[0],
        password_hash=None,
        is_active=True,
        is_verified=True,
        oauth_provider="firebase",
        oauth_id=firebase_uid,
    )
    db.add(user)
    await db.flush()
    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> CurrentUser:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if get_firebase_app() is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service not configured — set FIREBASE_SERVICE_ACCOUNT",
        )

    # Verify the Firebase ID token
    try:
        from firebase_admin import auth as firebase_auth
        decoded = firebase_auth.verify_id_token(credentials.credentials)
        firebase_uid: str = decoded["uid"]
        email: str = decoded.get("email", "")
        full_name: str = decoded.get("name", "")
    except Exception as exc:
        logger.debug("Firebase token verification failed: %s", exc)
        raise credentials_exception

    # Find or provision a local user row
    try:
        user = await _get_or_create_user(firebase_uid, email, full_name, db)
    except Exception as exc:
        logger.error("User lookup/create failed: %s", exc)
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    # Base permissions: every Firebase user gets rag:search.
    # Additional permissions can be stored as Firebase Custom Claims under "permissions".
    permissions: set[str] = {"rag:search"} | set(decoded.get("permissions", []))

    return CurrentUser(user=user, permissions=permissions, session_id=uuid.uuid4())


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
