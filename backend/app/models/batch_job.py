"""
Batch Job Models for Multi-Document Processing

Handles batch upload, processing, and tracking of multiple documents.
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
from uuid import uuid4


class BatchJobType(str, Enum):
    """Type of batch operation"""
    UPLOAD = "upload"
    PROCESS = "process"
    EXPORT = "export"
    DELETE = "delete"


class BatchJobStatus(str, Enum):
    """Status of batch job"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"  # Some succeeded, some failed


class BatchItemStatus(BaseModel):
    """Status of individual item in batch"""
    document_id: Optional[str] = None
    filename: str
    status: str  # success, failed, processing
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None


class BatchJob(BaseModel):
    """Batch job for processing multiple documents"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    job_type: BatchJobType
    status: BatchJobStatus = BatchJobStatus.PENDING

    # Items in batch
    total_items: int
    completed_items: int = 0
    failed_items: int = 0
    item_statuses: List[BatchItemStatus] = []

    # Configuration
    template_id: Optional[str] = None  # For batch processing
    collection_id: Optional[str] = None  # For grouping documents
    config: Dict[str, Any] = {}

    # Tracking
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None

    # Celery task tracking
    celery_task_ids: List[str] = []

    class Config:
        json_schema_extra = {
            "example": {
                "id": "batch_123",
                "user_id": "user_456",
                "job_type": "upload",
                "status": "processing",
                "total_items": 5,
                "completed_items": 3,
                "failed_items": 0,
                "config": {
                    "collection_name": "Project Phoenix Specs",
                    "tags": ["phoenix", "specifications"]
                }
            }
        }


class DocumentCollection(BaseModel):
    """Collection of related documents"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    name: str
    description: Optional[str] = None

    # Documents
    document_ids: List[str] = []
    document_count: int = 0

    # Metadata
    tags: List[str] = []
    project_name: Optional[str] = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "id": "collection_123",
                "user_id": "user_456",
                "name": "Project Phoenix Specifications",
                "description": "All specification documents for Project Phoenix",
                "document_ids": ["doc_1", "doc_2", "doc_3"],
                "document_count": 3,
                "tags": ["phoenix", "specifications"],
                "project_name": "Project Phoenix"
            }
        }
