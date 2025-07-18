from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.modules.users.models import User
from app.modules.users.schemas import UserCreate, UserUpdate, User as UserSchema
from app.core.security import get_password_hash
from app.core.cache import cache

class UserService:
    CACHE_PREFIX = "user"
    
    def __init__(self, db: Session):
        self.db = db

    async def _cache_user(self, user: User) -> None:
        """Cache user data"""
        if user:
            user_data = UserSchema.model_validate(user).model_dump()
            await cache.set([self.CACHE_PREFIX, "id", user.id], user_data)
            await cache.set([self.CACHE_PREFIX, "email", user.email], user_data)
            await cache.set([self.CACHE_PREFIX, "username", user.username], user_data)

    async def _invalidate_user_cache(self, user: User) -> None:
        """Invalidate user cache"""
        await cache.delete([self.CACHE_PREFIX, "id", user.id])
        await cache.delete([self.CACHE_PREFIX, "email", user.email])
        await cache.delete([self.CACHE_PREFIX, "username", user.username])

    async def create(self, user: UserCreate) -> User:
        db_user = User(
            email=user.email,
            username=user.username,
            hashed_password=get_password_hash(user.password)
        )
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        await self._cache_user(db_user)
        return db_user

    async def get_by_id(self, user_id: int) -> Optional[User]:
        # Try cache first
        cached_user = await cache.get([self.CACHE_PREFIX, "id", user_id])
        if cached_user:
            return UserSchema.model_validate_json(cached_user)
        
        # Query database
        stmt = select(User).where(User.id == user_id)
        user = self.db.execute(stmt).scalar_one_or_none()
        if user:
            await self._cache_user(user)
        return user

    async def get_by_email(self, email: str) -> Optional[User]:
        # Try cache first
        cached_user = await cache.get([self.CACHE_PREFIX, "email", email])
        if cached_user:
            return UserSchema.model_validate_json(cached_user)
        
        # Query database
        stmt = select(User).where(User.email == email)
        user = self.db.execute(stmt).scalar_one_or_none()
        if user:
            await self._cache_user(user)
        return user

    async def get_by_username(self, username: str) -> Optional[User]:
        # Try cache first
        cached_user = await cache.get([self.CACHE_PREFIX, "username", username])
        if cached_user:
            return UserSchema.model_validate_json(cached_user)
        
        # Query database
        stmt = select(User).where(User.username == username)
        user = self.db.execute(stmt).scalar_one_or_none()
        if user:
            await self._cache_user(user)
        return user

    async def list(self, skip: int = 0, limit: int = 100) -> List[User]:
        # For lists, we only cache the results briefly
        cache_key = [self.CACHE_PREFIX, "list", skip, limit]
        cached_users = await cache.get(cache_key)
        if cached_users:
            return [UserSchema.model_validate_json(u) for u in cached_users]
        
        # Query database
        stmt = select(User).offset(skip).limit(limit)
        users = self.db.execute(stmt).scalars().all()
        
        # Cache for a shorter time
        await cache.set(cache_key, [UserSchema.model_validate(u).model_dump() for u in users], expire=300)
        return users

    async def update(self, user_id: int, update_data: UserUpdate) -> Optional[User]:
        user = await self.get_by_id(user_id)
        if not user:
            return None

        # Update user fields
        update_dict = update_data.model_dump(exclude_unset=True)
        if "password" in update_dict:
            update_dict["hashed_password"] = get_password_hash(update_dict.pop("password"))
        
        for key, value in update_dict.items():
            setattr(user, key, value)

        self.db.commit()
        self.db.refresh(user)
        
        # Update cache
        await self._invalidate_user_cache(user)
        await self._cache_user(user)
        return user

    async def delete(self, user_id: int) -> bool:
        user = await self.get_by_id(user_id)
        if user:
            await self._invalidate_user_cache(user)
            self.db.delete(user)
            self.db.commit()
            return True
        return False
