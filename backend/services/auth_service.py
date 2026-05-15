import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.user import User
from core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from core.redis import get_redis
from core.config import settings
from datetime import timedelta


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(self, email: str, username: str, password: str, full_name: str | None = None) -> User:
        existing = await self.db.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none():
            raise ValueError("Email already registered")

        existing_username = await self.db.execute(select(User).where(User.username == username))
        if existing_username.scalar_one_or_none():
            raise ValueError("Username already taken")

        user = User(
            email=email,
            username=username,
            hashed_password=hash_password(password),
            full_name=full_name,
        )
        self.db.add(user)
        await self.db.flush()
        return user

    async def authenticate(self, email: str, password: str) -> User:
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user or not verify_password(password, user.hashed_password):
            raise ValueError("Invalid email or password")
        if not user.is_active:
            raise ValueError("Account is disabled")
        return user

    async def get_user_by_id(self, user_id: uuid.UUID) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def create_tokens(self, user: User) -> dict:
        access_token = create_access_token(str(user.id))
        refresh_token = create_refresh_token(str(user.id))

        redis = await get_redis()
        ttl = settings.jwt_refresh_token_expire_days * 86400
        await redis.setex(f"refresh:{user.id}:{refresh_token[-16:]}", ttl, "valid")

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }

    async def refresh_access_token(self, refresh_token: str) -> dict:
        try:
            payload = decode_token(refresh_token)
        except ValueError as exc:
            raise ValueError("Invalid refresh token") from exc

        if payload.get("type") != "refresh":
            raise ValueError("Invalid token type")

        user_id = payload.get("sub")
        redis = await get_redis()
        key = f"refresh:{user_id}:{refresh_token[-16:]}"
        if not await redis.exists(key):
            raise ValueError("Refresh token revoked or expired")

        user = await self.get_user_by_id(uuid.UUID(user_id))
        if not user or not user.is_active:
            raise ValueError("User not found or inactive")

        new_access = create_access_token(str(user.id))
        return {"access_token": new_access, "token_type": "bearer"}

    async def logout(self, user_id: str, refresh_token: str) -> None:
        redis = await get_redis()
        await redis.delete(f"refresh:{user_id}:{refresh_token[-16:]}")
