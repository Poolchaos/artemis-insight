"""
User service for database operations.
"""

from datetime import datetime
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.models.user import UserCreate, UserInDB
from app.utils.auth import hash_password


class UserService:
    """Service for user-related database operations."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db.users

    async def create_user(self, user_data: UserCreate) -> UserInDB:
        """Create a new user."""
        user_dict = {
            "email": user_data.email,
            "name": user_data.name,
            "hashed_password": hash_password(user_data.password),
            "is_active": True,
            "is_admin": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

        result = await self.collection.insert_one(user_dict)
        user_dict["_id"] = str(result.inserted_id)

        return UserInDB(**user_dict)

    async def get_user_by_email(self, email: str) -> Optional[UserInDB]:
        """Get user by email."""
        user_doc = await self.collection.find_one({"email": email})
        if user_doc:
            user_doc["_id"] = str(user_doc["_id"])
            return UserInDB(**user_doc)
        return None

    async def get_user_by_id(self, user_id: str) -> Optional[UserInDB]:
        """Get user by ID."""
        if not ObjectId.is_valid(user_id):
            return None

        user_doc = await self.collection.find_one({"_id": ObjectId(user_id)})
        if user_doc:
            user_doc["_id"] = str(user_doc["_id"])
            return UserInDB(**user_doc)
        return None

    async def email_exists(self, email: str) -> bool:
        """Check if email already exists."""
        count = await self.collection.count_documents({"email": email})
        return count > 0

    async def update_user(self, user_id: str, update_data: dict) -> Optional[UserInDB]:
        """Update user data."""
        if not ObjectId.is_valid(user_id):
            return None

        update_data["updated_at"] = datetime.utcnow()

        result = await self.collection.find_one_and_update(
            {"_id": ObjectId(user_id)},
            {"$set": update_data},
            return_document=True
        )

        if result:
            result["_id"] = str(result["_id"])
            return UserInDB(**result)
        return None
