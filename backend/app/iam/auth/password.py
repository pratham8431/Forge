import hashlib
import secrets
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def hash_token(token: str) -> str:
    """SHA-256 hash a token before storing in Redis/DB — never store raw."""
    return hashlib.sha256(token.encode()).hexdigest()


def generate_otp(length: int = 64) -> str:
    """Cryptographically secure random token for email verify / password reset."""
    return secrets.token_urlsafe(length)
