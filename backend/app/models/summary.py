"""
Summary models for AI-generated document summaries.

Stores the results from multi-pass AI processing using templates.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field, field_validator
from bson import ObjectId

from app.models.user import PyObjectId


class SummaryStatus(str, Enum):
    """Summary generation status."""
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class SummarySection(BaseModel):
    """A single section within a generated summary."""

    title: str = Field(..., description="Section title from template")
    order: int = Field(..., description="Display order of this section")
    content: str = Field(..., description="AI-generated section content")
    source_chunks: int = Field(..., description="Number of source chunks used")
    pages_referenced: List[int] = Field(default_factory=list, description="Source PDF page numbers")
    word_count: int = Field(..., description="Word count of generated content")
    generated_at: datetime = Field(..., description="When this section was generated")

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Introduction",
                "order": 1,
                "content": "The proposed water treatment facility aims to...",
                "source_chunks": 15,
                "pages_referenced": [1, 2, 3, 5, 8],
                "word_count": 285,
                "generated_at": "2025-11-16T10:30:00Z"
            }
        }


class ProcessingMetadata(BaseModel):
    """Metadata about the document processing."""

    total_pages: int = Field(..., description="Total pages in source PDF")
    total_words: int = Field(..., description="Total words extracted from PDF")
    total_chunks: int = Field(..., description="Total chunks created")
    embedding_count: int = Field(..., description="Number of embeddings generated")
    processing_duration_seconds: Optional[float] = Field(default=None, description="Total processing time")
    estimated_cost_usd: Optional[float] = Field(default=None, description="Estimated OpenAI API cost")

    class Config:
        json_schema_extra = {
            "example": {
                "total_pages": 401,
                "total_words": 147618,
                "total_chunks": 300,
                "embedding_count": 300,
                "processing_duration_seconds": 285.5,
                "estimated_cost_usd": 1.85
            }
        }


class SummaryBase(BaseModel):
    """Base summary schema."""

    template_id: str = Field(..., description="Template used for generation")
    template_name: str = Field(..., description="Template name (denormalized for quick access)")
    status: SummaryStatus = Field(default=SummaryStatus.PROCESSING, description="Generation status")
    sections: List[SummarySection] = Field(default_factory=list, description="Generated sections")
    metadata: Optional[ProcessingMetadata] = Field(default=None, description="Processing metadata")
    error_message: Optional[str] = Field(default=None, description="Error message if generation failed")


class SummaryCreate(BaseModel):
    """Schema for creating a new summary."""

    document_id: str = Field(..., description="Associated document ID")
    user_id: str = Field(..., description="User ID who owns the document")
    template_id: str = Field(..., description="Template to use for generation")
    template_name: str = Field(..., description="Template name")
    job_id: Optional[str] = Field(default=None, description="Associated job ID for tracking")

    @field_validator('document_id', 'user_id', 'template_id')
    @classmethod
    def validate_object_ids(cls, v: str) -> str:
        """Validate IDs are valid ObjectIds."""
        if not ObjectId.is_valid(v):
            raise ValueError(f"Invalid ObjectId: {v}")
        return v


class SummaryUpdate(BaseModel):
    """Schema for updating summary fields."""

    status: Optional[SummaryStatus] = None
    sections: Optional[List[SummarySection]] = None
    metadata: Optional[ProcessingMetadata] = None
    error_message: Optional[str] = None
    completed_at: Optional[datetime] = None


class SummaryInDB(SummaryBase):
    """Summary schema as stored in database."""

    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    document_id: PyObjectId = Field(..., description="Associated document ID")
    user_id: PyObjectId = Field(..., description="User ID")
    job_id: Optional[PyObjectId] = Field(default=None, description="Associated job ID")
    started_at: datetime = Field(default_factory=datetime.utcnow, description="When processing started")
    completed_at: Optional[datetime] = Field(default=None, description="When processing completed")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {PyObjectId: str, datetime: lambda v: v.isoformat()}


class SummaryResponse(BaseModel):
    """Summary schema for API responses."""

    id: str = Field(..., description="Summary ID")
    document_id: str = Field(..., description="Document ID")
    user_id: str = Field(..., description="User ID")
    job_id: Optional[str] = Field(default=None, description="Job ID")
    template_id: str = Field(..., description="Template ID")
    template_name: str = Field(..., description="Template name")
    status: SummaryStatus
    sections: List[SummarySection]
    metadata: Optional[ProcessingMetadata] = None
    error_message: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class SummaryListItem(BaseModel):
    """Condensed summary info for list views."""

    id: str
    document_id: str
    template_name: str
    status: SummaryStatus
    section_count: int = Field(..., description="Number of sections generated")
    total_word_count: int = Field(..., description="Total words in all sections")
    started_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat()}
