"""
Auth router — Firebase edition.

Registration, login, password reset, and email verification are now handled
entirely by the Firebase client SDK on the frontend.  This router only exposes
the small set of endpoints that still need a backend:

  GET  /auth/me            — return current user's profile
  POST /auth/logout-all    — revoke all Firebase refresh tokens (sign out everywhere)
  GET  /auth/sessions      — stub that returns current session (Firebase has no list API)
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.iam.access.middleware import get_current_user, CurrentUser

router = APIRouter(prefix="/auth", tags=["Authentication"])


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


@router.post("/logout-all")
async def logout_all(current: CurrentUser = Depends(get_current_user)):
    """Revoke all Firebase refresh tokens for this user (signs out all devices)."""
    from app.core.firebase import get_firebase_app

    if get_firebase_app() is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth service not configured",
        )

    try:
        from firebase_admin import auth as firebase_auth
        firebase_auth.revoke_refresh_tokens(current.user.oauth_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke sessions: {exc}",
        )

    return {"message": "All sessions revoked"}


@router.get("/sessions")
async def get_sessions(current: CurrentUser = Depends(get_current_user)):
    """
    Firebase manages sessions client-side; we return the caller's own session
    as a single-element list so the UI has something to render.
    """
    from datetime import datetime, timezone, timedelta

    return [
        {
            "id": str(current.session_id),
            "device_name": "Current session",
            "ip_address": None,
            "last_used": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    ]
