import uuid
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status, Request
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from redis.asyncio import Redis
from user_agents import parse as parse_ua

from app.core.config import settings
from app.iam.identity.models import User, Session, Role, AuditAction
from app.iam.auth.password import hash_password, verify_password, hash_token, generate_otp
from app.iam.auth.jwt import (
    create_access_token, create_refresh_token,
    decode_refresh_token,
)
from app.iam.auth.schemas import (
    RegisterRequest, LoginRequest, TokenResponse, UserOut, SessionOut,
)
from app.iam.security.rate_limiter import check_login_rate_limit
from app.iam.security.account_lock import (
    is_account_locked, record_failed_attempt, clear_failed_attempts
)
from app.workers.audit_tasks import log_audit_event
from app.workers.email_tasks import send_verification_email, send_password_reset_email


_GENERIC_AUTH_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid credentials",
)


def _get_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    return forwarded.split(",")[0].strip() if forwarded else request.client.host


def _parse_device(user_agent_str: str) -> dict:
    ua = parse_ua(user_agent_str)
    return {
        "device": ua.device.family,
        "browser": ua.browser.family,
        "os": ua.os.family,
        "device_name": f"{ua.browser.family} on {ua.os.family}",
    }


async def _get_user_permissions(user: User) -> list[str]:
    perms = set()
    for role in user.roles:
        for perm in role.permissions:
            perms.add(perm.name)
    return list(perms)


async def _load_user_with_roles(db: AsyncSession, user_id: uuid.UUID) -> User:
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(User)
        .options(selectinload(User.roles).selectinload(Role.permissions))
        .where(User.id == user_id, User.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


# ─── Register ─────────────────────────────────────────────────────────────────

async def register_user(data: RegisterRequest, db: AsyncSession, redis: Redis) -> dict:
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        full_name=data.full_name,
        is_active=True,
        is_verified=False,
    )
    db.add(user)
    await db.flush()

    # Assign default "developer" role
    role_result = await db.execute(select(Role).where(Role.name == "developer"))
    default_role = role_result.scalar_one_or_none()
    if default_role:
        user.roles.append(default_role)

    await db.commit()
    await db.refresh(user)

    # Send verification email via Celery (non-blocking)
    otp = generate_otp(48)
    otp_hash = hash_token(otp)
    await redis.setex(f"verify:email:{otp_hash}", 86400, str(user.id))  # 24h TTL
    send_verification_email.delay(user.email, user.full_name, otp)

    log_audit_event.delay(str(user.id), AuditAction.REGISTER.value)

    return {"message": "Registration successful. Please verify your email."}


# ─── Verify Email ─────────────────────────────────────────────────────────────

async def verify_email(token: str, db: AsyncSession, redis: Redis) -> dict:
    token_hash = hash_token(token)
    user_id_str = await redis.get(f"verify:email:{token_hash}")
    if not user_id_str:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")

    user = await db.get(User, uuid.UUID(user_id_str))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_verified = True
    await db.commit()
    await redis.delete(f"verify:email:{token_hash}")
    log_audit_event.delay(str(user.id), AuditAction.EMAIL_VERIFIED.value)

    return {"message": "Email verified successfully"}


# ─── Login ────────────────────────────────────────────────────────────────────

async def login_user(
    data: LoginRequest, request: Request, db: AsyncSession, redis: Redis
) -> TokenResponse:
    ip = _get_ip(request)
    ua_string = request.headers.get("User-Agent", "")

    # Rate limit check
    allowed = await check_login_rate_limit(redis, ip)
    if not allowed:
        raise HTTPException(status_code=429, detail="Too many login attempts. Try again later.")

    # Account lock check
    if await is_account_locked(redis, data.email):
        raise HTTPException(status_code=423, detail="Account temporarily locked. Try again in 15 minutes.")

    # Fetch user
    result = await db.execute(select(User).where(User.email == data.email, User.deleted_at.is_(None)))
    user = result.scalar_one_or_none()

    if not user or not user.password_hash or not verify_password(data.password, user.password_hash):
        if user:
            await record_failed_attempt(redis, data.email)
            log_audit_event.delay(str(user.id), AuditAction.LOGIN_FAILURE.value, ip)
        raise _GENERIC_AUTH_ERROR

    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Please verify your email before logging in.")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled.")

    # Clear any previous fail counters
    await clear_failed_attempts(redis, data.email)

    # Load roles and permissions
    user = await _load_user_with_roles(db, user.id)
    permissions = await _get_user_permissions(user)

    # Create session
    session_id = uuid.uuid4()
    refresh_token = create_refresh_token(user.id, session_id)
    access_token = create_access_token(user.id, user.email, permissions)

    token_hash = hash_token(refresh_token)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    ua_info = _parse_device(ua_string)
    session = Session(
        id=session_id,
        user_id=user.id,
        refresh_token_hash=token_hash,
        device_name=ua_info["device_name"],
        ip_address=ip,
        user_agent=ua_string,
        expires_at=expires_at,
    )
    db.add(session)
    await db.commit()

    log_audit_event.delay(str(user.id), AuditAction.LOGIN_SUCCESS.value, ip, metadata={"device": ua_info["device_name"]})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserOut.model_validate(user),
    )


# ─── Refresh Token Rotation ───────────────────────────────────────────────────

async def refresh_tokens(refresh_token: str, db: AsyncSession, redis: Redis) -> TokenResponse:
    try:
        payload = decode_refresh_token(refresh_token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    token_hash = hash_token(refresh_token)
    session_id = uuid.UUID(payload["session_id"])
    user_id = uuid.UUID(payload["sub"])

    # Find session by hash
    result = await db.execute(
        select(Session).where(Session.id == session_id, Session.refresh_token_hash == token_hash)
    )
    session = result.scalar_one_or_none()
    if not session or session.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired or revoked")

    # Load user with roles
    user = await _load_user_with_roles(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    permissions = await _get_user_permissions(user)

    # Token rotation — delete old, issue new
    new_refresh_token = create_refresh_token(user.id, session_id)
    new_access_token = create_access_token(user.id, user.email, permissions)
    new_hash = hash_token(new_refresh_token)
    new_expires = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    session.refresh_token_hash = new_hash
    session.expires_at = new_expires
    session.last_used = datetime.now(timezone.utc)
    await db.commit()

    log_audit_event.delay(str(user.id), AuditAction.TOKEN_REFRESHED.value)

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        user=UserOut.model_validate(user),
    )


# ─── Logout ───────────────────────────────────────────────────────────────────

async def logout_user(session_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession) -> dict:
    await db.execute(
        delete(Session).where(Session.id == session_id, Session.user_id == user_id)
    )
    await db.commit()
    log_audit_event.delay(str(user_id), AuditAction.LOGOUT.value)
    return {"message": "Logged out successfully"}


async def logout_all_sessions(user_id: uuid.UUID, db: AsyncSession) -> dict:
    await db.execute(delete(Session).where(Session.user_id == user_id))
    await db.commit()
    log_audit_event.delay(str(user_id), AuditAction.ALL_SESSIONS_REVOKED.value)
    return {"message": "All sessions revoked"}


# ─── Password Reset ───────────────────────────────────────────────────────────

async def forgot_password(email: str, db: AsyncSession, redis: Redis) -> dict:
    result = await db.execute(select(User).where(User.email == email, User.deleted_at.is_(None)))
    user = result.scalar_one_or_none()

    # Always return success to prevent user enumeration
    if not user:
        return {"message": "If that email exists, a reset link has been sent."}

    otp = generate_otp(48)
    otp_hash = hash_token(otp)
    await redis.setex(f"pwd_reset:{otp_hash}", 3600, str(user.id))  # 1h TTL
    send_password_reset_email.delay(user.email, user.full_name, otp)
    log_audit_event.delay(str(user.id), AuditAction.PASSWORD_RESET_REQUESTED.value)

    return {"message": "If that email exists, a reset link has been sent."}


async def reset_password(token: str, new_password: str, db: AsyncSession, redis: Redis) -> dict:
    token_hash = hash_token(token)
    user_id_str = await redis.get(f"pwd_reset:{token_hash}")
    if not user_id_str:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user = await db.get(User, uuid.UUID(user_id_str))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.password_hash = hash_password(new_password)
    await db.commit()
    await redis.delete(f"pwd_reset:{token_hash}")

    # Invalidate all sessions after password reset
    await db.execute(delete(Session).where(Session.user_id == user.id))
    await db.commit()

    log_audit_event.delay(str(user.id), AuditAction.PASSWORD_RESET_COMPLETED.value)
    return {"message": "Password reset successfully. Please log in again."}


# ─── Sessions ─────────────────────────────────────────────────────────────────

async def get_user_sessions(user_id: uuid.UUID, db: AsyncSession) -> list[SessionOut]:
    result = await db.execute(select(Session).where(Session.user_id == user_id))
    sessions = result.scalars().all()
    return [SessionOut.model_validate(s) for s in sessions]


async def revoke_session(session_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession) -> dict:
    result = await db.execute(
        select(Session).where(Session.id == session_id, Session.user_id == user_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    await db.delete(session)
    await db.commit()
    log_audit_event.delay(str(user_id), AuditAction.SESSION_REVOKED.value, metadata={"session_id": str(session_id)})
    return {"message": "Session revoked"}
