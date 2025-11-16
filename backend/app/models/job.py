"""
Job model for tracking asynchronous processing tasks.
"""

from datetime import datetime
from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field, field_validator

from app.models.user import PyObjectId


class JobType(str, Enum):
    """Job type enumeration."""
    UPLOAD = "upload"
    EXTRACT = "extract"
    SUMMARIZE = "summarize"
    EMBED = "embed"


class JobStatus(str, Enum):
    """Job status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobBase(BaseModel):
    """Base job schema."""
    job_type: JobType = Field(..., description="Type of job")
    status: JobStatus = Field(default=JobStatus.PENDING, description="Current job status")
    progress: int = Field(default=0, ge=0, le=100, description="Job progress percentage")
    error_message: Optional[str] = Field(default=None, description="Error message if job failed")


class JobCreate(JobBase):
    """Schema for creating a new job."""
    user_id: str = Field(..., description="User ID who initiated the job")
    document_id: str = Field(..., description="Associated document ID")
    celery_task_id: Optional[str] = Field(default=None, description="Celery task ID")

    @field_validator('user_id', 'document_id')
    @classmethod
    def validate_object_ids(cls, v: str) -> str:
        """Validate IDs are valid ObjectIds."""
        PyObjectId.validate(v, None)
        return v


class JobUpdate(BaseModel):
    """Schema for updating job fields."""
    status: Optional[JobStatus] = None
    progress: Optional[int] = Field(default=None, ge=0, le=100)
    error_message: Optional[str] = None
    completed_at: Optional[datetime] = None


class JobInDB(JobBase):
    """Job schema as stored in database."""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId = Field(..., description="User ID who initiated the job")
    document_id: PyObjectId = Field(..., description="Associated document ID")
    celery_task_id: Optional[str] = Field(default=None, description="Celery task ID")
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {PyObjectId: str, datetime: lambda v: v.isoformat()}


class JobResponse(BaseModel):
    """Job schema for API responses."""
    id: str = Field(..., description="Job ID")
    user_id: str = Field(..., description="User ID")
    document_id: str = Field(..., description="Document ID")
    job_type: JobType
    status: JobStatus
    progress: int
    error_message: Optional[str] = None
    celery_task_id: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat()}
