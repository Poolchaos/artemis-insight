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
        """Establish MongoDB connection with connection pooling."""
        self.client = AsyncIOMotorClient(
            settings.mongo_uri,
            maxPoolSize=50,  # Maximum connections in pool
            minPoolSize=10,  # Minimum connections to maintain
            maxIdleTimeMS=30000,  # Close idle connections after 30s
            serverSelectionTimeoutMS=5000,  # Timeout for server selection
            connectTimeoutMS=10000,  # Timeout for initial connection
            socketTimeoutMS=20000,  # Timeout for socket operations
        )
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
        if self.db is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self.db


# Global database manager instance
db_manager = DatabaseManager()


def get_db() -> AsyncIOMotorDatabase:
    """Dependency for route handlers to get database instance."""
    return db_manager.get_database()
