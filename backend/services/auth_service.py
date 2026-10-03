"""Authentication helpers: password hashing, session tokens, and roles."""

import hashlib
import hmac
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from models import User, UserSession

logger = logging.getLogger(__name__)

# In production this should be a strong random value stored in a secret manager.
_SECRET = os.getenv("AUTH_SECRET", "change-me-in-production").encode()
SESSION_TTL_HOURS = int(os.getenv("SESSION_TTL_HOURS", "24"))

VALID_ROLES = {"user", "admin"}


def _hash_password(password: str) -> str:
    """Hash a password with a per-user salt using PBKDF2-HMAC-SHA256."""
    salt = secrets.token_hex(16)
    iterations = 200_000
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations)
    return f"pbkdf2_sha256${iterations}${salt}${dk.hex()}"


def _verify_password(password: str, hashed: str) -> bool:
    """Verify a password against a stored hash."""
    try:
        algorithm, iterations, salt, stored = hashed.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(iterations))
        return hmac.compare_digest(dk.hex(), stored)
    except (ValueError, AttributeError):
        return False


def create_user(
    db: Session,
    email: str,
    password: str,
    full_name: Optional[str] = None,
    role: Optional[str] = None,
) -> User:
    """Create a new user with a hashed password.

    The first registered user is bootstrapped as the platform
    admin so a fresh deployment always has exactly one admin
    without manual setup. Subsequent users default to the
    'user' role; only an explicit role argument (used by
    admin-managed creation) can assign 'admin'.
    """
    if db.query(User).filter(User.email == email.lower()).first():
        raise ValueError("A user with this email already exists")

    if role is not None and role not in VALID_ROLES:
        raise ValueError(f"role must be one of {sorted(VALID_ROLES)}")

    if db.query(User).count() == 0:
        assigned_role = "admin"
        logger.info("Bootstrapping first user as admin")
    else:
        assigned_role = role or "user"

    user = User(
        email=email.lower(),
        hashed_password=_hash_password(password),
        full_name=full_name,
        role=assigned_role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """Authenticate a user by email and password."""
    user = db.query(User).filter(User.email == email.lower()).first()
    if user is None or not user.is_active:
        return None
    if not _verify_password(password, user.hashed_password):
        return None
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    return user


def create_session(db: Session, user_id: int) -> str:
    """Create a new session for a user and return the raw token."""
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=SESSION_TTL_HOURS)
    session = UserSession(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(session)
    db.commit()
    return token


def _as_utc(value: datetime) -> datetime:
    """Normalize a stored datetime to UTC-aware.

    SQLite does not preserve timezone information, so values
    read back from the database may be naive. Treating them
    as UTC keeps expiry comparisons correct across backends.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def get_user_from_token(db: Session, token: str) -> Optional[User]:
    """Resolve a session token to a user, refreshing last_used_at."""
    if not token:
        return None
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    session = db.query(UserSession).filter(UserSession.token_hash == token_hash).first()
    if session is None:
        return None
    if _as_utc(session.expires_at) < datetime.now(timezone.utc):
        db.delete(session)
        db.commit()
        return None
    session.last_used_at = datetime.now(timezone.utc)
    db.commit()
    return db.query(User).filter(User.id == session.user_id).first()


def revoke_session(db: Session, token: str) -> bool:
    """Revoke a session token."""
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    session = db.query(UserSession).filter(UserSession.token_hash == token_hash).first()
    if session:
        db.delete(session)
        db.commit()
        return True
    return False


def revoke_all_sessions(db: Session, user_id: int) -> int:
    """Revoke every active session for a user. Returns the count."""
    sessions = db.query(UserSession).filter(UserSession.user_id == user_id).all()
    for session in sessions:
        db.delete(session)
    db.commit()
    return len(sessions)


def set_user_role(db: Session, user_id: int, role: str) -> Optional[User]:
    """Change a user's role. Returns the updated user, or None."""
    if role not in VALID_ROLES:
        raise ValueError(f"role must be one of {sorted(VALID_ROLES)}")
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        return None
    user.role = role
    db.commit()
    db.refresh(user)
    return user


def set_user_active(db: Session, user_id: int, is_active: bool) -> Optional[User]:
    """Activate or deactivate a user account."""
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        return None
    user.is_active = is_active
    if not is_active:
        # Deactivating a user invalidates all of their sessions.
        revoke_all_sessions(db, user_id)
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user_id: int) -> bool:
    """Permanently delete a user and their sessions."""
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        return False
    revoke_all_sessions(db, user_id)
    db.delete(user)
    db.commit()
    return True
