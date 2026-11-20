
from datetime import datetime, timedelta, timezone
from typing import Callable

import jwt
from pwdlib import PasswordHash
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from backend import db
from backend.config import settings


# ---------- Security Configuration ----------

password_hash = PasswordHash.recommended()

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/login"
)

ALGORITHM = "HS256"

CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid or expired authentication credentials",
    headers={"WWW-Authenticate": "Bearer"}
)


# ---------- Password Management ----------

def hash_password(password: str) -> str:
    """Hash a password using Argon2."""
    return password_hash.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str
) -> bool:
    """Verify a password against its stored hash."""
    return password_hash.verify(
        plain_password,
        hashed_password
    )


# ---------- Initial Administrator ----------

def ensure_admin_user() -> None:
    """
    Create the initial administrator if it does not exist.

    Synchronizes the administrator password hash with environment configuration.
    """

    username = (settings.admin_username or "admin").strip()
    password = settings.admin_password or "admin_password_123"

    if len(password) < 12:
        password = "admin_password_123"

    existing = db.users().find_one({"username": username})

    if existing:
        if existing.get("role") != "admin":
            raise RuntimeError(
                "Configured administrator username already belongs "
                "to a non-admin account."
            )
        # Synchronize password hash with current environment configuration
        db.users().update_one(
            {"username": username},
            {"$set": {"password_hash": hash_password(password), "active": True}}
        )
        return

    db.users().insert_one({
        "username": username,
        "password_hash": hash_password(password),
        "role": "admin",
        "active": True,
        "created_at": datetime.now(timezone.utc)
    })


# ---------- Employee Account Creation ----------

def create_employee_user(
    username: str,
    password: str
) -> dict:
    """Create an employee account."""

    username = username.strip()

    if not username:
        raise HTTPException(
            status_code=400,
            detail="Username is required."
        )

    if len(password) < 12:
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least 12 characters."
        )

    if db.users().find_one({"username": username}):
        raise HTTPException(
            status_code=409,
            detail="Username already exists."
        )

    user = {
        "username": username,
        "password_hash": hash_password(password),
        "role": "employee",
        "active": True,
        "created_at": datetime.now(timezone.utc)
    }

    db.users().insert_one(user)

    return {
        "username": username,
        "role": "employee",
        "active": True
    }


def reset_user_password(
    username: str,
    new_password: str
) -> dict:
    """Reset an account password."""

    username = username.strip()

    if not username:
        raise HTTPException(
            status_code=400,
            detail="Username is required."
        )

    if len(new_password) < 12:
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least 12 characters."
        )

    user = db.users().find_one({"username": username})

    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"User '{username}' not found."
        )

    db.users().update_one(
        {"username": username},
        {
            "$set": {
                "password_hash": hash_password(new_password),
                "updated_at": datetime.now(timezone.utc)
            }
        }
    )

    return {
        "username": username,
        "message": f"Password for user '{username}' has been successfully reset."
    }


# ---------- Login Authentication ----------

def authenticate_user(
    username: str,
    password: str
):
    """Validate username and password against MongoDB."""

    user = db.users().find_one({
        "username": username,
        "active": True
    })

    if not user:
        return None

    if not verify_password(
        password,
        user["password_hash"]
    ):
        return None

    return {
        "username": user["username"],
        "role": user["role"],
        "active": user["active"]
    }


# ---------- JWT Token Generation ----------

def create_access_token(
    username: str,
    expires_delta: timedelta | None = None
) -> str:
    """Generate a signed JWT access token."""

    if not settings.jwt_secret_key:
        raise RuntimeError("JWT secret is not configured.")

    if expires_delta is None:
        expires_delta = timedelta(
            minutes=settings.jwt_access_token_expire_minutes
        )

    expire = datetime.now(timezone.utc) + expires_delta

    payload = {
        "sub": username,
        "exp": expire
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=ALGORITHM
    )


# ---------- Current User Verification ----------

def get_current_user(
    token: str = Depends(oauth2_scheme)
) -> dict:
    """Decode the JWT and retrieve the active user from MongoDB."""

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[ALGORITHM]
        )

        username = payload.get("sub")

        if not username:
            raise CREDENTIALS_EXCEPTION

    except jwt.InvalidTokenError:
        raise CREDENTIALS_EXCEPTION

    user = db.users().find_one({
        "username": username,
        "active": True
    })

    if not user:
        raise CREDENTIALS_EXCEPTION

    return {
        "username": user["username"],
        "role": user["role"],
        "active": user["active"]
    }


# ---------- Role-Based Authorization ----------

def require_role(*allowed_roles: str) -> Callable:
    """Restrict an endpoint to specified user roles."""

    def role_checker(
        current_user: dict = Depends(get_current_user)
    ) -> dict:

        if current_user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource."
            )

        return current_user

    return role_checker
