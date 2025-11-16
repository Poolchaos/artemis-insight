"""
Integration tests for authentication routes.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import create_application
from app.database import get_db


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


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient, test_db):
    """Test successful user registration."""
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "newuser@example.com",
            "name": "New User",
            "password": "SecurePass123"
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "newuser@example.com"
    assert data["user"]["name"] == "New User"
    assert "password" not in data["user"]


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, test_db):
    """Test registration with duplicate email."""
    # First registration
    await client.post(
        "/api/auth/register",
        json={
            "email": "duplicate@example.com",
            "name": "First User",
            "password": "SecurePass123"
        }
    )

    # Attempt duplicate registration
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "duplicate@example.com",
            "name": "Second User",
            "password": "AnotherPass456"
        }
    )

    assert response.status_code == 400
    assert "already registered" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_invalid_email(client: AsyncClient):
    """Test registration with invalid email format."""
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "not-an-email",
            "name": "Test User",
            "password": "SecurePass123"
        }
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_db):
    """Test successful login."""
    # Register user first
    await client.post(
        "/api/auth/register",
        json={
            "email": "logintest@example.com",
            "name": "Login Test",
            "password": "SecurePass123"
        }
    )

    # Login
    response = await client.post(
        "/api/auth/login",
        json={
            "email": "logintest@example.com",
            "password": "SecurePass123"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["email"] == "logintest@example.com"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, test_db):
    """Test login with incorrect password."""
    # Register user first
    await client.post(
        "/api/auth/register",
        json={
            "email": "wrongpass@example.com",
            "name": "Wrong Pass Test",
            "password": "CorrectPass123"
        }
    )

    # Login with wrong password
    response = await client.post(
        "/api/auth/login",
        json={
            "email": "wrongpass@example.com",
            "password": "WrongPass456"
        }
    )

    assert response.status_code == 401
    assert "incorrect" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    """Test login with non-existent user."""
    response = await client.post(
        "/api/auth/login",
        json={
            "email": "nonexistent@example.com",
            "password": "SomePass123"
        }
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user(client: AsyncClient, test_db):
    """Test getting current user information."""
    # Register and get tokens
    register_response = await client.post(
        "/api/auth/register",
        json={
            "email": "currentuser@example.com",
            "name": "Current User",
            "password": "SecurePass123"
        }
    )

    access_token = register_response.json()["access_token"]

    # Get current user
    response = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "currentuser@example.com"
    assert data["name"] == "Current User"
    assert "password" not in data


@pytest.mark.asyncio
async def test_get_current_user_no_token(client: AsyncClient):
    """Test getting current user without authentication."""
    response = await client.get("/api/auth/me")

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient, test_db):
    """Test token refresh."""
    # Register and get tokens
    register_response = await client.post(
        "/api/auth/register",
        json={
            "email": "refreshtest@example.com",
            "name": "Refresh Test",
            "password": "SecurePass123"
        }
    )

    refresh_token = register_response.json()["refresh_token"]

    # Refresh token
    response = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": refresh_token}
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_refresh_with_access_token_fails(client: AsyncClient, test_db):
    """Test that refresh endpoint rejects access tokens."""
    # Register and get tokens
    register_response = await client.post(
        "/api/auth/register",
        json={
            "email": "accesstokentest@example.com",
            "name": "Access Token Test",
            "password": "SecurePass123"
        }
    )

    access_token = register_response.json()["access_token"]

    # Try to refresh with access token
    response = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": access_token}
    )

    assert response.status_code == 401
