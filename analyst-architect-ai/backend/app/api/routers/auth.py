"""
Auth router:
  POST /auth/login     — получить JWT токен
  GET  /auth/me        — профиль текущего пользователя
  POST /auth/register  — регистрация (только admin)
  GET  /auth/users     — список пользователей (только admin)
  PATCH /auth/users/{id} — изменить роль/статус (только admin)
  POST /auth/users/{id}/reset-password — сброс пароля (только admin)
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.services.auth_service import (
    authenticate_user, create_user, create_access_token,
    hash_password, get_user_by_username,
)
from app.api.deps import get_current_user, require_admin

router = APIRouter(prefix="/auth", tags=["auth"])

# ── Schemas ───────────────────────────────────────────────────────────────────

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str
    role: str
    full_name: str

class UserOut(BaseModel):
    id: str
    username: str
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True

class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: str = Field(min_length=5, max_length=200)
    password: str = Field(min_length=6, max_length=100)
    full_name: str = Field(default="", max_length=200)
    role: str = Field(default="analyst", pattern="^(admin|analyst|architect)$")

class UpdateUserRequest(BaseModel):
    role: Optional[str] = Field(default=None, pattern="^(admin|analyst|architect)$")
    is_active: Optional[bool] = None
    full_name: Optional[str] = None

class ResetPasswordRequest(BaseModel):
    new_password: str = Field(min_length=6, max_length=100)

# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenOut)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Authenticate with username + password, get JWT access token."""
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token({"sub": user.id, "role": user.role})
    return TokenOut(
        access_token=token,
        user_id=user.id,
        username=user.username,
        role=user.role,
        full_name=user.full_name,
    )


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)):
    """Return current user's profile."""
    return current_user


@router.post("/register", response_model=UserOut)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Register a new user (admin only)."""
    existing = await get_user_by_username(db, body.username)
    if existing:
        raise HTTPException(400, f"Username '{body.username}' already taken")
    user = await create_user(
        db, body.username, body.email, body.password,
        body.full_name, body.role,
    )
    return user


@router.get("/users", response_model=List[UserOut])
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """List all users (admin only)."""
    res = await db.execute(select(User).order_by(User.created_at))
    return res.scalars().all()


@router.patch("/users/{user_id}", response_model=UserOut)
async def update_user(
    user_id: str,
    body: UpdateUserRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Update user role/status/name (admin only)."""
    res = await db.execute(select(User).where(User.id == user_id))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")
    if body.role is not None:
        user.role = body.role
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.full_name is not None:
        user.full_name = body.full_name
    user.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/users/{user_id}/reset-password")
async def reset_password(
    user_id: str,
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Reset user password (admin only)."""
    res = await db.execute(select(User).where(User.id == user_id))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")
    user.hashed_password = hash_password(body.new_password)
    user.updated_at = datetime.utcnow()
    await db.commit()
    return {"status": "ok", "message": f"Password reset for {user.username}"}
