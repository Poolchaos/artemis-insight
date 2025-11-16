"""
Pytest configuration and shared fixtures.
"""

import pytest
import asyncio
from typing import AsyncGenerator
from motor.motor_asyncio import AsyncIOMotorClient


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_db() -> AsyncGenerator:
    """Provide test database instance."""
    client = AsyncIOMotorClient("mongodb://admin:devpassword123@mongodb:27017/?authSource=admin")
    db = client.artemis_insight_test

    yield db

    # Cleanup - drop collections instead of database to avoid auth issues
    collections = await db.list_collection_names()
    for collection in collections:
        await db.drop_collection(collection)

    client.close()
