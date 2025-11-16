"""
MongoDB database connection and management.
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Optional

from app.config import settings


class DatabaseManager:
    """Manages MongoDB connection and provides database access."""

    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None

    async def connect(self) -> None:
        """Establish MongoDB connection."""
        self.client = AsyncIOMotorClient(settings.mongo_uri)
        self.db = self.client.get_default_database()

        # Verify connection
        await self.client.admin.command('ping')
        print(f"Connected to MongoDB: {self.db.name}")

    async def disconnect(self) -> None:
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            print("Disconnected from MongoDB")

    def get_database(self) -> AsyncIOMotorDatabase:
        """Get database instance."""
        if not self.db:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self.db


# Global database manager instance
db_manager = DatabaseManager()


def get_db() -> AsyncIOMotorDatabase:
    """Dependency for route handlers to get database instance."""
    return db_manager.get_database()
