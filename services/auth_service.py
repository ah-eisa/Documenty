"""Single-user authentication and password utilities."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from config import settings
from database.models import AuthSession

PASSWORD_ITERATIONS = 310_000


def hash_password(password: str) -> str:
    if len(password) < 12:
        raise ValueError("Password must contain at least 12 characters")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PASSWORD_ITERATIONS)
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(digest).decode()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt, digest = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), base64.urlsafe_b64decode(salt), int(iterations))
        return hmac.compare_digest(candidate, base64.urlsafe_b64decode(digest))
    except (ValueError, TypeError):
        return False


def authenticate(db, password: str) -> str | None:
    if not settings.AUTH_PASSWORD_HASH or not verify_password(password, settings.AUTH_PASSWORD_HASH):
        return None
    raw_token = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.SESSION_TTL_HOURS)
    db.add(AuthSession(token_hash=token_hash, expires_at=expires_at))
    db.commit()
    return raw_token


def get_session(db, raw_token: str | None) -> AuthSession | None:
    if not raw_token:
        return None
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    session = db.query(AuthSession).filter(AuthSession.token_hash == token_hash).first()
    if not session:
        return None
    expires = session.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires <= datetime.now(timezone.utc):
        db.delete(session)
        db.commit()
        return None
    return session


def revoke(db, raw_token: str | None) -> None:
    session = get_session(db, raw_token)
    if session:
        db.delete(session)
        db.commit()


def password_hash_command(password: str) -> str:
    return hash_password(password)


if __name__ == "__main__":
    import getpass
    print(password_hash_command(getpass.getpass("Password: ")))
