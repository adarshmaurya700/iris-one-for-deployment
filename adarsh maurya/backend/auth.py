"""
Authentication module for IRIS one.
Provides bcrypt password hashing, JWT token generation & verification,
and FastAPI dependencies for user authentication.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import os
import sqlite3
import warnings
import bcrypt
import jwt
from fastapi import Request, HTTPException, status, Depends

import env_loader  # noqa: F401

# Suppress pyjwt HMAC key length recommendation warning for the specified secret key
warnings.filterwarnings("ignore", category=UserWarning, module="jwt")

from database import get_db, db_session, row_to_dict

SECRET_KEY = os.environ.get("JWT_SECRET") or "iris_one_secret_key_2026"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24


def hash_password(password: str) -> str:
    """Hashes a plaintext password using bcrypt with a salt."""
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verifies a plaintext password against a bcrypt hash, supporting legacy demo passwords."""
    if not password or not password_hash:
        return False
    if password == password_hash:
        return True
    try:
        pwd_bytes = password.encode("utf-8")
        hash_bytes = password_hash.encode("utf-8")
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except Exception:
        return False


def create_token(user_id: int) -> str:
    """Generates a signed JWT access token valid for 24 hours."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": expire,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> int:
    """
    Decodes and validates a JWT token. Returns the user_id (int).
    Raises HTTPException 401 if invalid or expired.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str = payload.get("sub")
        if user_id_str is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing subject identifier",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return int(user_id_str)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except (jwt.PyJWTError, ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def _extract_token_from_header(request: Request) -> Optional[str]:
    """Extracts the Bearer token string from the Authorization header if present."""
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None
    parts = auth_header.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    elif len(parts) == 1:
        # Fallback in case raw token was provided in header
        return parts[0]
    return None


def get_current_user(request: Request, db: sqlite3.Connection = Depends(db_session)) -> Dict[str, Any]:
    """
    Dependency that extracts the JWT token from the Authorization header,
    decodes it, and fetches the corresponding user from the database.
    Raises HTTPException 401 if unauthorized.
    """
    token = _extract_token_from_header(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing or invalid. Use 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = decode_token(token)
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User belonging to this token no longer exists.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_dict = row_to_dict(row)
    # Remove sensitive password hash from returned user object
    if user_dict and "password_hash" in user_dict:
        del user_dict["password_hash"]

    return user_dict


def get_optional_current_user(request: Request, db: sqlite3.Connection = Depends(db_session)) -> Optional[Dict[str, Any]]:
    """
    Dependency that attempts to extract and authenticate current user,
    but returns None instead of raising an error if unauthenticated.
    """
    token = _extract_token_from_header(request)
    if not token:
        return None

    try:
        user_id = decode_token(token)
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if not row:
            return None
        user_dict = row_to_dict(row)
        if user_dict and "password_hash" in user_dict:
            del user_dict["password_hash"]
        return user_dict
    except Exception:
        return None


def get_workspace_user(request: Request, db=Depends(db_session)):
    """Anonymous demo access is explicit; an expired token must not write to the demo."""
    if request.headers.get('Authorization'):
        return get_current_user(request, db)
    return None
