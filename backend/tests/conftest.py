"""
Pytest configuration and shared fixtures.
"""

import pytest
import asyncio
from typing import AsyncGenerator
from motor.motor_asyncio import AsyncIOMotorClient
from httpx import AsyncClient, ASGITransport
from app.main import create_application
from app.database import get_db


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


@pytest.fixture
async def app(test_db):
    """Create application for testing with test database."""
    application = create_application()

    # Override database dependency with test database
    async def override_get_db():
        return test_db

    application.dependency_overrides[get_db] = override_get_db

    yield application

    # Clean up
    application.dependency_overrides.clear()


@pytest.fixture
async def client(app):
    """Create async HTTP client for testing."""
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def test_user(test_db):
    """Create a test user."""
    from app.services.user_service import UserService
    from app.models.user import UserCreate

    user_service = UserService(test_db)
    user_data = UserCreate(
        email="testuser@example.com",
        name="Test User",  # UserCreate expects 'name' not 'full_name'
        password="password123"
    )
    user = await user_service.create_user(user_data)
    return user


@pytest.fixture
def access_token(test_user):
    """Create access token for test user."""
    from app.utils.auth import create_access_token
    return create_access_token(str(test_user.id))


@pytest.fixture
async def admin_user(test_db):
    """Create a test admin user."""
    from app.services.user_service import UserService
    from app.models.user import UserCreate, UserInDB
    from bson import ObjectId

    user_service = UserService(test_db)
    user_data = UserCreate(
        email="admin@example.com",
        name="Admin User",
        password="adminpass123"
    )
    admin = await user_service.create_user(user_data)

    # Manually set is_admin to True in the database
    await test_db.users.update_one(
        {"_id": ObjectId(admin.id)},
        {"$set": {"is_admin": True}}
    )

    # Fetch updated user
    updated_user = await test_db.users.find_one({"_id": ObjectId(admin.id)})
    # Convert _id to string for UserInDB
    updated_user["_id"] = str(updated_user["_id"])
    return UserInDB(**updated_user)


@pytest.fixture
def admin_token(admin_user):
    """Create access token for admin user."""
    from app.utils.auth import create_access_token
    return create_access_token(str(admin_user.id))
