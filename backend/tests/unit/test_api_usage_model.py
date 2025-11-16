"""
Unit tests for API usage model.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError
from bson import ObjectId

from app.models.api_usage import (
    ApiUsageBase,
    ApiUsageCreate,
    ApiUsageInDB,
    ApiUsageResponse,
    ApiUsageStats
)


def test_api_usage_base_valid():
    """Test valid API usage base creation."""
    usage = ApiUsageBase(
        endpoint="/api/documents",
        method="POST",
        status_code=201,
        response_time=45.5,
        ip_address="192.168.1.1"
    )
    assert usage.endpoint == "/api/documents"
    assert usage.method == "POST"
    assert usage.status_code == 201
    assert usage.response_time == 45.5


def test_api_usage_base_method_normalization():
    """Test HTTP method is normalized to uppercase."""
    usage = ApiUsageBase(
        endpoint="/api/users",
        method="get",
        status_code=200,
        response_time=10.0
    )
    assert usage.method == "GET"


def test_api_usage_base_invalid_method():
    """Test API usage with invalid HTTP method."""
    with pytest.raises(ValidationError) as exc_info:
        ApiUsageBase(
            endpoint="/api/test",
            method="INVALID",
            status_code=200,
            response_time=10.0
        )
    assert "Method must be one of" in str(exc_info.value)


def test_api_usage_base_invalid_status_code():
    """Test API usage with invalid status code."""
    with pytest.raises(ValidationError) as exc_info:
        ApiUsageBase(
            endpoint="/api/test",
            method="GET",
            status_code=99,
            response_time=10.0
        )
    assert "greater than or equal to 100" in str(exc_info.value)


def test_api_usage_base_status_code_too_high():
    """Test API usage with status code exceeding limit."""
    with pytest.raises(ValidationError) as exc_info:
        ApiUsageBase(
            endpoint="/api/test",
            method="GET",
            status_code=600,
            response_time=10.0
        )
    assert "less than or equal to 599" in str(exc_info.value)


def test_api_usage_base_negative_response_time():
    """Test API usage with negative response time."""
    with pytest.raises(ValidationError) as exc_info:
        ApiUsageBase(
            endpoint="/api/test",
            method="GET",
            status_code=200,
            response_time=-5.0
        )
    assert "greater than or equal to 0" in str(exc_info.value)


def test_api_usage_base_ipv4_address():
    """Test API usage with valid IPv4 address."""
    usage = ApiUsageBase(
        endpoint="/api/test",
        method="GET",
        status_code=200,
        response_time=10.0,
        ip_address="10.0.0.1"
    )
    assert usage.ip_address == "10.0.0.1"


def test_api_usage_base_ipv6_address():
    """Test API usage with valid IPv6 address."""
    usage = ApiUsageBase(
        endpoint="/api/test",
        method="GET",
        status_code=200,
        response_time=10.0,
        ip_address="2001:0db8:85a3:0000:0000:8a2e:0370:7334"
    )
    assert usage.ip_address == "2001:0db8:85a3:0000:0000:8a2e:0370:7334"


def test_api_usage_base_invalid_ip_address():
    """Test API usage with invalid IP address."""
    with pytest.raises(ValidationError) as exc_info:
        ApiUsageBase(
            endpoint="/api/test",
            method="GET",
            status_code=200,
            response_time=10.0,
            ip_address="not-an-ip"
        )
    assert "Invalid IP address" in str(exc_info.value)


def test_api_usage_create_with_user():
    """Test API usage creation with authenticated user."""
    user_id = str(ObjectId())
    usage = ApiUsageCreate(
        user_id=user_id,
        endpoint="/api/documents",
        method="GET",
        status_code=200,
        response_time=25.0
    )
    assert usage.user_id == user_id


def test_api_usage_create_without_user():
    """Test API usage creation without user (anonymous)."""
    usage = ApiUsageCreate(
        endpoint="/api/health",
        method="GET",
        status_code=200,
        response_time=5.0
    )
    assert usage.user_id is None


def test_api_usage_create_invalid_user_id():
    """Test API usage create with invalid user ID."""
    with pytest.raises(ValidationError) as exc_info:
        ApiUsageCreate(
            user_id="invalid-id",
            endpoint="/api/test",
            method="GET",
            status_code=200,
            response_time=10.0
        )
    assert "Invalid ObjectId" in str(exc_info.value)


def test_api_usage_in_db():
    """Test API usage in database schema."""
    usage = ApiUsageInDB(
        user_id=ObjectId(),
        endpoint="/api/documents",
        method="POST",
        status_code=201,
        response_time=50.0,
        ip_address="192.168.1.100"
    )
    assert usage.id is not None
    assert isinstance(usage.timestamp, datetime)


def test_api_usage_in_db_anonymous():
    """Test API usage in DB without user."""
    usage = ApiUsageInDB(
        endpoint="/api/health",
        method="GET",
        status_code=200,
        response_time=2.0
    )
    assert usage.user_id is None


def test_api_usage_response():
    """Test API usage API response schema."""
    response = ApiUsageResponse(
        id=str(ObjectId()),
        user_id=str(ObjectId()),
        endpoint="/api/documents",
        method="GET",
        status_code=200,
        response_time=30.0,
        ip_address="10.0.0.1",
        timestamp=datetime.utcnow()
    )
    assert response.endpoint == "/api/documents"
    assert response.status_code == 200


def test_api_usage_stats():
    """Test API usage statistics schema."""
    stats = ApiUsageStats(
        total_requests=1000,
        successful_requests=950,
        failed_requests=50,
        avg_response_time=25.5,
        requests_by_endpoint={"/api/documents": 500, "/api/users": 500},
        requests_by_method={"GET": 700, "POST": 300},
        period_start=datetime(2025, 1, 1),
        period_end=datetime(2025, 1, 31)
    )
    assert stats.total_requests == 1000
    assert stats.successful_requests == 950
    assert stats.avg_response_time == 25.5
