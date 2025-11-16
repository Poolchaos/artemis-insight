"""
Unit tests for user service.
"""

import pytest
from datetime import datetime

from app.services.user_service import UserService
from app.models.user import UserCreate


@pytest.mark.asyncio
async def test_create_user(test_db):
    """Test creating a new user."""
    user_service = UserService(test_db)

    user_data = UserCreate(
        email="test@example.com",
        name="Test User",
        password="testpassword123"
    )

    user = await user_service.create_user(user_data)

    assert user.email == "test@example.com"
    assert user.name == "Test User"
    assert user.hashed_password != "testpassword123"
    assert user.is_active is True
    assert user.is_admin is False
    assert isinstance(user.created_at, datetime)


@pytest.mark.asyncio
async def test_get_user_by_email(test_db):
    """Test retrieving user by email."""
    user_service = UserService(test_db)

    # Create user
    user_data = UserCreate(
        email="test@example.com",
        name="Test User",
        password="testpassword123"
    )
    created_user = await user_service.create_user(user_data)

    # Retrieve user
    retrieved_user = await user_service.get_user_by_email("test@example.com")

    assert retrieved_user is not None
    assert retrieved_user.email == created_user.email
    assert retrieved_user.id == created_user.id


@pytest.mark.asyncio
async def test_get_user_by_email_not_found(test_db):
    """Test retrieving non-existent user by email."""
    user_service = UserService(test_db)

    user = await user_service.get_user_by_email("nonexistent@example.com")

    assert user is None


@pytest.mark.asyncio
async def test_get_user_by_id(test_db):
    """Test retrieving user by ID."""
    user_service = UserService(test_db)

    # Create user
    user_data = UserCreate(
        email="test@example.com",
        name="Test User",
        password="testpassword123"
    )
    created_user = await user_service.create_user(user_data)

    # Retrieve user by ID
    retrieved_user = await user_service.get_user_by_id(created_user.id)

    assert retrieved_user is not None
    assert retrieved_user.id == created_user.id
    assert retrieved_user.email == created_user.email


@pytest.mark.asyncio
async def test_get_user_by_id_invalid(test_db):
    """Test retrieving user with invalid ID."""
    user_service = UserService(test_db)

    user = await user_service.get_user_by_id("invalid_id")

    assert user is None


@pytest.mark.asyncio
async def test_email_exists(test_db):
    """Test checking if email exists."""
    user_service = UserService(test_db)

    # Initially should not exist
    assert await user_service.email_exists("test@example.com") is False

    # Create user
    user_data = UserCreate(
        email="test@example.com",
        name="Test User",
        password="testpassword123"
    )
    await user_service.create_user(user_data)

    # Now should exist
    assert await user_service.email_exists("test@example.com") is True


@pytest.mark.asyncio
async def test_update_user(test_db):
    """Test updating user data."""
    user_service = UserService(test_db)

    # Create user
    user_data = UserCreate(
        email="test@example.com",
        name="Test User",
        password="testpassword123"
    )
    created_user = await user_service.create_user(user_data)

    # Update user
    updated_user = await user_service.update_user(
        created_user.id,
        {"name": "Updated Name"}
    )

    assert updated_user is not None
    assert updated_user.name == "Updated Name"
    assert updated_user.email == created_user.email
    assert updated_user.updated_at > created_user.updated_at
