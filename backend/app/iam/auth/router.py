import uuid
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.core.database import get_db
from app.core.redis import get_redis
from app.iam.auth.schemas import (
    RegisterRequest, LoginRequest, RefreshRequest,
    VerifyEmailRequest, ForgotPasswordRequest, ResetPasswordRequest,
    TokenResponse, MessageResponse, SessionOut,
)
from app.iam.auth import service
from app.iam.access.middleware import get_current_user, CurrentUser

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=MessageResponse, status_code=201)
async def register(
    data: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    return await service.register_user(data, db, redis)


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(
    data: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    return await service.verify_email(data.token, db, redis)


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    return await service.login_user(data, request, db, redis)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    data: RefreshRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    return await service.refresh_tokens(data.refresh_token, db, redis)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.logout_user(current.session_id, current.user.id, db)


@router.post("/logout-all", response_model=MessageResponse)
async def logout_all(
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.logout_all_sessions(current.user.id, db)


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    data: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    return await service.forgot_password(data.email, db, redis)


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    return await service.reset_password(data.token, data.new_password, db, redis)


@router.get("/me")
async def get_me(current: CurrentUser = Depends(get_current_user)):
    return {
        "id": str(current.user.id),
        "email": current.user.email,
        "full_name": current.user.full_name,
        "is_verified": current.user.is_verified,
        "roles": [r.name for r in current.user.roles],
        "permissions": list(current.permissions),
    }


@router.get("/sessions", response_model=list[SessionOut])
async def get_sessions(
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.get_user_sessions(current.user.id, db)


@router.delete("/sessions/{session_id}", response_model=MessageResponse)
async def revoke_session(
    session_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await service.revoke_session(session_id, current.user.id, db)
