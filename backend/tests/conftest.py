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
    client = AsyncIOMotorClient("mongodb://admin:testpass@mongodb:27017")
    db = client.artemis_insight_test

    yield db

    # Cleanup
    await client.drop_database("artemis_insight_test")
    client.close()
