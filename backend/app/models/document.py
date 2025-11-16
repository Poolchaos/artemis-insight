"""
Document model for PDF document metadata and processing status.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, field_validator

from app.models.user import PyObjectId


class DocumentStatus(str, Enum):
    """Document processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentBase(BaseModel):
    """Base document schema."""
    filename: str = Field(..., min_length=1, max_length=255, description="Original filename")
    file_path: str = Field(..., description="MinIO object storage path")
    file_size: int = Field(..., gt=0, description="File size in bytes")
    mime_type: str = Field(default="application/pdf", description="MIME type of the document")
    status: DocumentStatus = Field(default=DocumentStatus.PENDING, description="Processing status")
    processing_metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional processing metadata")

    @field_validator('mime_type')
    @classmethod
    def validate_mime_type(cls, v: str) -> str:
        """Validate MIME type is a PDF."""
        allowed_types = ["application/pdf"]
        if v not in allowed_types:
            raise ValueError(f"MIME type must be one of {allowed_types}")
        return v


class DocumentCreate(DocumentBase):
    """Schema for creating a new document."""
    user_id: str = Field(..., description="User ID who uploaded the document")

    @field_validator('user_id')
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        """Validate user_id is a valid ObjectId."""
        PyObjectId.validate(v, None)
        return v


class DocumentUpdate(BaseModel):
    """Schema for updating document fields."""
    status: Optional[DocumentStatus] = None
    processing_metadata: Optional[Dict[str, Any]] = None


class DocumentInDB(DocumentBase):
    """Document schema as stored in database."""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId = Field(..., description="User ID who uploaded the document")
    upload_date: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {PyObjectId: str, datetime: lambda v: v.isoformat()}


class DocumentResponse(BaseModel):
    """Document schema for API responses."""
    id: str = Field(..., description="Document ID")
    user_id: str = Field(..., description="User ID")
    filename: str
    file_path: str
    file_size: int
    mime_type: str
    status: DocumentStatus
    processing_metadata: Optional[Dict[str, Any]] = None
    upload_date: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat()}
