"""
Unit tests for authentication utilities.
"""

import pytest
from datetime import datetime, timedelta

from app.utils.auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token
)
from app.models.user import TokenPayload


def test_hash_password():
    """Test password hashing."""
    password = "testpassword123"
    hashed = hash_password(password)

    assert hashed != password
    assert len(hashed) > 0


def test_verify_password_correct():
    """Test password verification with correct password."""
    password = "testpassword123"
    hashed = hash_password(password)

    assert verify_password(password, hashed) is True


def test_verify_password_incorrect():
    """Test password verification with incorrect password."""
    password = "testpassword123"
    hashed = hash_password(password)

    assert verify_password("wrongpassword", hashed) is False


def test_create_access_token():
    """Test access token creation."""
    user_id = "507f1f77bcf86cd799439011"
    token = create_access_token(user_id)

    assert isinstance(token, str)
    assert len(token) > 0

    # Decode and verify
    payload = decode_token(token)
    assert payload is not None
    assert payload.sub == user_id
    assert payload.type == "access"


def test_create_refresh_token():
    """Test refresh token creation."""
    user_id = "507f1f77bcf86cd799439011"
    token = create_refresh_token(user_id)

    assert isinstance(token, str)
    assert len(token) > 0

    # Decode and verify
    payload = decode_token(token)
    assert payload is not None
    assert payload.sub == user_id
    assert payload.type == "refresh"


def test_decode_token_valid():
    """Test decoding valid token."""
    user_id = "507f1f77bcf86cd799439011"
    token = create_access_token(user_id)

    payload = decode_token(token)

    assert payload is not None
    assert payload.sub == user_id
    assert payload.type == "access"
    assert payload.exp > int(datetime.utcnow().timestamp())


def test_decode_token_invalid():
    """Test decoding invalid token."""
    invalid_token = "invalid.token.string"

    payload = decode_token(invalid_token)

    assert payload is None


def test_token_expiration():
    """Test that token contains proper expiration."""
    user_id = "507f1f77bcf86cd799439011"

    # Access token
    access_token = create_access_token(user_id)
    access_payload = decode_token(access_token)
    assert access_payload is not None

    expected_access_exp = datetime.utcnow() + timedelta(minutes=15)
    actual_access_exp = datetime.fromtimestamp(access_payload.exp)
    assert abs((actual_access_exp - expected_access_exp).total_seconds()) < 5

    # Refresh token
    refresh_token = create_refresh_token(user_id)
    refresh_payload = decode_token(refresh_token)
    assert refresh_payload is not None

    expected_refresh_exp = datetime.utcnow() + timedelta(days=7)
    actual_refresh_exp = datetime.fromtimestamp(refresh_payload.exp)
    assert abs((actual_refresh_exp - expected_refresh_exp).total_seconds()) < 5
