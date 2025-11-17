"""
Document model for PDF document metadata and processing status.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
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
    page_count: Optional[int] = Field(default=None, ge=0, description="Number of pages in the document")
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
    page_count: Optional[int] = None
    processing_metadata: Optional[Dict[str, Any]] = None
    upload_date: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat()}


# ============================================================================
# Semantic Search Models
# ============================================================================

class SearchQuery(BaseModel):
    """Schema for document search query."""
    query: str = Field(..., min_length=1, max_length=500, description="Natural language search query")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of results to return")
    min_similarity: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum similarity threshold")


class SearchResult(BaseModel):
    """Schema for a single search result chunk."""
    chunk_id: str = Field(..., description="Unique chunk identifier")
    content: str = Field(..., description="Chunk text content")
    page_number: int = Field(..., description="Page number in document")
    similarity_score: float = Field(..., description="Cosine similarity score (0-1)")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional chunk metadata")


class SearchResponse(BaseModel):
    """Schema for search results response."""
    document_id: str = Field(..., description="Document ID that was searched")
    query: str = Field(..., description="Original search query")
    results: List[SearchResult] = Field(..., description="List of matching chunks")
    total_chunks_searched: int = Field(..., description="Total number of chunks in document")
    search_duration_ms: float = Field(..., description="Search execution time in milliseconds")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
