"""
Authentication service.
- bcrypt password hashing
- JWT access tokens (HS256)
- Role-based access control helpers
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.models.user import User

# ── Password hashing ──────────────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

# ── JWT ───────────────────────────────────────────────────────────────────────
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8  # 8 hours

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.APP_SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.APP_SECRET_KEY, algorithms=[ALGORITHM])

# ── DB helpers ────────────────────────────────────────────────────────────────
async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    res = await db.execute(select(User).where(User.username == username))
    return res.scalar_one_or_none()

async def get_user_by_id(db: AsyncSession, user_id: str) -> Optional[User]:
    res = await db.execute(select(User).where(User.id == user_id))
    return res.scalar_one_or_none()

async def authenticate_user(db: AsyncSession, username: str, password: str) -> Optional[User]:
    user = await get_user_by_username(db, username)
    if not user or not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    # Update last_login
    user.last_login = datetime.utcnow()
    await db.commit()
    return user

async def create_user(
    db: AsyncSession,
    username: str,
    email: str,
    password: str,
    full_name: str = "",
    role: str = "analyst",
) -> User:
    user = User(
        id=str(uuid.uuid4()),
        username=username,
        email=email,
        full_name=full_name,
        hashed_password=hash_password(password),
        role=role,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

async def seed_default_users(db: AsyncSession):
    """Create default admin, analyst, and architect accounts if they don't exist."""
    defaults = [
        ("admin",     "admin@analystguru.local",     "admin123",     "System Administrator", "admin"),
        ("analyst",   "analyst@analystguru.local",   "analyst123",   "Senior Analyst",       "analyst"),
        ("architect", "architect@analystguru.local", "architect123", "Lead Architect",       "architect"),
    ]
    for username, email, password, full_name, role in defaults:
        existing = await get_user_by_username(db, username)
        if not existing:
            await create_user(db, username, email, password, full_name, role)

# ── Role checks ───────────────────────────────────────────────────────────────
ROLE_PERMISSIONS = {
    "admin": {
        "can_manage_users", "can_manage_settings", "can_delete_documents",
        "can_view_audit", "can_review_documents", "can_add_kb", "can_view_all",
        "can_generate_diagrams", "can_manage_memory",
    },
    "analyst": {
        "can_review_documents", "can_add_kb", "can_view_audit",
        "can_view_all", "can_generate_diagrams", "can_manage_memory",
    },
    "architect": {
        "can_review_documents", "can_add_kb", "can_view_audit",
        "can_view_all", "can_generate_diagrams", "can_manage_memory",
        "can_manage_settings",
    },
}

def has_permission(user: User, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(user.role, set())
