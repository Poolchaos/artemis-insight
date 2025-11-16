"""
API Usage model for tracking and analytics of API calls.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from ipaddress import IPv4Address, IPv6Address

from app.models.user import PyObjectId


class ApiUsageBase(BaseModel):
    """Base API usage schema."""
    endpoint: str = Field(..., description="API endpoint path")
    method: str = Field(..., description="HTTP method")
    status_code: int = Field(..., ge=100, le=599, description="HTTP status code")
    response_time: float = Field(..., ge=0, description="Response time in milliseconds")
    ip_address: Optional[str] = Field(default=None, description="Client IP address")

    @field_validator('method')
    @classmethod
    def validate_method(cls, v: str) -> str:
        """Validate HTTP method."""
        allowed_methods = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"]
        v_upper = v.upper()
        if v_upper not in allowed_methods:
            raise ValueError(f"Method must be one of {allowed_methods}")
        return v_upper

    @field_validator('ip_address')
    @classmethod
    def validate_ip_address(cls, v: Optional[str]) -> Optional[str]:
        """Validate IP address format."""
        if v is not None:
            try:
                # Try parsing as IPv4 or IPv6
                IPv4Address(v)
            except ValueError:
                try:
                    IPv6Address(v)
                except ValueError:
                    raise ValueError("Invalid IP address format")
        return v


class ApiUsageCreate(ApiUsageBase):
    """Schema for creating a new API usage record."""
    user_id: Optional[str] = Field(default=None, description="User ID if authenticated")

    @field_validator('user_id')
    @classmethod
    def validate_user_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate user_id is a valid ObjectId if provided."""
        if v is not None:
            PyObjectId.validate(v, None)
        return v


class ApiUsageInDB(ApiUsageBase):
    """API usage schema as stored in database."""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: Optional[PyObjectId] = Field(default=None, description="User ID if authenticated")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {PyObjectId: str, datetime: lambda v: v.isoformat()}


class ApiUsageResponse(BaseModel):
    """API usage schema for API responses."""
    id: str = Field(..., description="Usage record ID")
    user_id: Optional[str] = Field(default=None, description="User ID")
    endpoint: str
    method: str
    status_code: int
    response_time: float
    ip_address: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class ApiUsageStats(BaseModel):
    """Schema for API usage statistics."""
    total_requests: int = Field(..., description="Total number of requests")
    successful_requests: int = Field(..., description="Number of successful requests (2xx status)")
    failed_requests: int = Field(..., description="Number of failed requests (4xx, 5xx status)")
    avg_response_time: float = Field(..., description="Average response time in milliseconds")
    requests_by_endpoint: dict = Field(..., description="Request count by endpoint")
    requests_by_method: dict = Field(..., description="Request count by HTTP method")
    period_start: datetime = Field(..., description="Start of statistics period")
    period_end: datetime = Field(..., description="End of statistics period")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
