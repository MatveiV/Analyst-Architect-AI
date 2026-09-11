"""
FastAPI dependencies for authentication and authorization.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.services.auth_service import decode_token, get_user_by_id

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
oauth2_optional = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate JWT; return current user. Raises 401 on failure."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        user_id: str = payload.get("sub")
        if not user_id:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await get_user_by_id(db, user_id)
    if not user or not user.is_active:
        raise credentials_exception
    return user


async def get_current_user_optional(
    token: str = Depends(oauth2_optional),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Like get_current_user but returns None instead of raising 401."""
    if not token:
        return None
    try:
        payload = decode_token(token)
        user_id: str = payload.get("sub")
        if not user_id:
            return None
        return await get_user_by_id(db, user_id)
    except Exception:
        return None


def require_roles(*roles: str):
    """Dependency factory: allow only specific roles."""
    async def _check(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role(s): {', '.join(roles)}",
            )
        return current_user
    return _check


# ── Shorthand dependencies ────────────────────────────────────────────────────
require_admin     = require_roles("admin")
require_analyst   = require_roles("admin", "analyst", "architect")
require_architect = require_roles("admin", "architect")
