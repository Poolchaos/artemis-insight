"""
Batch Processing API Routes

Endpoints for batch upload, job tracking, and document collections.
"""
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Form
from typing import List, Optional
from pydantic import BaseModel, Field

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import UserInDB
from app.models.batch_job import (
    BatchJob,
    BatchJobType,
    BatchJobStatus,
    DocumentCollection
)
from app.services.batch_processor import BatchProcessor
from app.services.document_service import DocumentService
from app.services.minio_service import MinIOService

router = APIRouter(prefix="/api/batch", tags=["batch"])


# Pydantic models for request/response
class CreateCollectionRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    document_ids: List[str] = Field(..., min_items=1)
    description: Optional[str] = Field(None, max_length=1000)
    tags: Optional[List[str]] = Field(default_factory=list)
    project_name: Optional[str] = Field(None, max_length=200)


class UpdateCollectionRequest(BaseModel):
    add_document_ids: Optional[List[str]] = None
    remove_document_ids: Optional[List[str]] = None
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)


class BatchJobResponse(BaseModel):
    id: str
    user_id: str
    job_type: BatchJobType
    status: BatchJobStatus
    total_items: int
    completed_items: int
    failed_items: int
    item_statuses: List[dict]
    config: dict
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]
    collection_id: Optional[str] = None


class CollectionResponse(BaseModel):
    id: str
    user_id: str
    name: str
    description: Optional[str]
    document_ids: List[str]
    document_count: int
    tags: List[str]
    project_name: Optional[str]
    created_at: str
    updated_at: str


def get_batch_processor(
    db=Depends(get_db),
    current_user: UserInDB = Depends(get_current_user)
):
    """Dependency to create BatchProcessor instance"""
    document_service = DocumentService(db)
    minio_service = MinIOService()
    return BatchProcessor(db, document_service, minio_service)


@router.post("/upload", response_model=BatchJobResponse)
async def batch_upload(
    files: List[UploadFile] = File(..., description="Multiple files to upload"),
    collection_name: Optional[str] = Form(None, description="Optional collection name"),
    tags: Optional[str] = Form(None, description="Comma-separated tags"),
    project_name: Optional[str] = Form(None, description="Optional project name"),
    current_user: UserInDB = Depends(get_current_user),
    batch_processor: BatchProcessor = Depends(get_batch_processor)
):
    """
    Upload multiple documents in a batch.
    Optionally create a collection to group them.

    - **files**: List of files to upload (PDF format)
    - **collection_name**: Optional name for document collection
    - **tags**: Optional comma-separated tags to apply to all documents
    - **project_name**: Optional project name for organization
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    if len(files) > 50:
        raise HTTPException(
            status_code=400,
            detail="Maximum 50 files allowed per batch upload"
        )

    # Validate file types
    for file in files:
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type for {file.filename}. Only PDF files are supported."
            )

    # Parse tags
    tag_list = [tag.strip() for tag in tags.split(',')] if tags else None

    # Start batch upload
    batch_job = await batch_processor.batch_upload(
        files=files,
        user_id=current_user.id,
        collection_name=collection_name,
        tags=tag_list,
        project_name=project_name
    )

    return BatchJobResponse(
        id=batch_job.id,
        user_id=batch_job.user_id,
        job_type=batch_job.job_type,
        status=batch_job.status,
        total_items=batch_job.total_items,
        completed_items=batch_job.completed_items,
        failed_items=batch_job.failed_items,
        item_statuses=batch_job.item_statuses,
        config=batch_job.config,
        created_at=batch_job.created_at.isoformat(),
        started_at=batch_job.started_at.isoformat() if batch_job.started_at else None,
        completed_at=batch_job.completed_at.isoformat() if batch_job.completed_at else None,
        collection_id=batch_job.collection_id
    )


@router.get("/jobs/{job_id}", response_model=BatchJobResponse)
async def get_batch_job(
    job_id: str,
    current_user: UserInDB = Depends(get_current_user),
    batch_processor: BatchProcessor = Depends(get_batch_processor)
):
    """
    Get status of a batch job by ID.

    Use this endpoint to poll for progress updates during batch processing.
    """
    batch_job = await batch_processor.get_batch_job(job_id, current_user.id)

    if not batch_job:
        raise HTTPException(status_code=404, detail="Batch job not found")

    return BatchJobResponse(
        id=batch_job.id,
        user_id=batch_job.user_id,
        job_type=batch_job.job_type,
        status=batch_job.status,
        total_items=batch_job.total_items,
        completed_items=batch_job.completed_items,
        failed_items=batch_job.failed_items,
        item_statuses=batch_job.item_statuses,
        config=batch_job.config,
        created_at=batch_job.created_at.isoformat(),
        started_at=batch_job.started_at.isoformat() if batch_job.started_at else None,
        completed_at=batch_job.completed_at.isoformat() if batch_job.completed_at else None,
        collection_id=batch_job.collection_id
    )


@router.get("/jobs", response_model=List[BatchJobResponse])
async def list_batch_jobs(
    job_type: Optional[BatchJobType] = None,
    status: Optional[BatchJobStatus] = None,
    limit: int = 50,
    current_user: UserInDB = Depends(get_current_user),
    batch_processor: BatchProcessor = Depends(get_batch_processor)
):
    """
    List batch jobs for the current user.

    - **job_type**: Optional filter by job type (UPLOAD, PROCESS, EXPORT, DELETE)
    - **status**: Optional filter by status (PENDING, PROCESSING, COMPLETED, FAILED, PARTIAL)
    - **limit**: Maximum number of jobs to return (default: 50, max: 100)
    """
    if limit > 100:
        limit = 100

    jobs = await batch_processor.list_batch_jobs(
        user_id=current_user.id,
        job_type=job_type,
        status=status,
        limit=limit
    )

    return [
        BatchJobResponse(
            id=job.id,
            user_id=job.user_id,
            job_type=job.job_type,
            status=job.status,
            total_items=job.total_items,
            completed_items=job.completed_items,
            failed_items=job.failed_items,
            item_statuses=job.item_statuses,
            config=job.config,
            created_at=job.created_at.isoformat(),
            started_at=job.started_at.isoformat() if job.started_at else None,
            completed_at=job.completed_at.isoformat() if job.completed_at else None,
            collection_id=job.collection_id
        )
        for job in jobs
    ]


@router.post("/collections", response_model=CollectionResponse)
async def create_collection(
    request: CreateCollectionRequest,
    current_user: UserInDB = Depends(get_current_user),
    batch_processor: BatchProcessor = Depends(get_batch_processor)
):
    """
    Create a new document collection.

    Collections group related documents together for easier organization and management.
    """
    collection = await batch_processor.create_collection(
        user_id=current_user.id,
        name=request.name,
        document_ids=request.document_ids,
        description=request.description,
        tags=request.tags,
        project_name=request.project_name
    )

    return CollectionResponse(
        id=collection.id,
        user_id=collection.user_id,
        name=collection.name,
        description=collection.description,
        document_ids=collection.document_ids,
        document_count=collection.document_count,
        tags=collection.tags,
        project_name=collection.project_name,
        created_at=collection.created_at.isoformat(),
        updated_at=collection.updated_at.isoformat()
    )


@router.get("/collections/{collection_id}", response_model=CollectionResponse)
async def get_collection(
    collection_id: str,
    current_user: UserInDB = Depends(get_current_user),
    batch_processor: BatchProcessor = Depends(get_batch_processor)
):
    """Get a document collection by ID"""
    collection = await batch_processor.get_collection(collection_id, current_user.id)

    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    return CollectionResponse(
        id=collection.id,
        user_id=collection.user_id,
        name=collection.name,
        description=collection.description,
        document_ids=collection.document_ids,
        document_count=collection.document_count,
        tags=collection.tags,
        project_name=collection.project_name,
        created_at=collection.created_at.isoformat(),
        updated_at=collection.updated_at.isoformat()
    )


@router.get("/collections", response_model=List[CollectionResponse])
async def list_collections(
    limit: int = 100,
    current_user: UserInDB = Depends(get_current_user),
    batch_processor: BatchProcessor = Depends(get_batch_processor)
):
    """
    List all document collections for the current user.

    - **limit**: Maximum number of collections to return (default: 100, max: 200)
    """
    if limit > 200:
        limit = 200

    collections = await batch_processor.list_collections(
        user_id=current_user.id,
        limit=limit
    )

    return [
        CollectionResponse(
            id=coll.id,
            user_id=coll.user_id,
            name=coll.name,
            description=coll.description,
            document_ids=coll.document_ids,
            document_count=coll.document_count,
            tags=coll.tags,
            project_name=coll.project_name,
            created_at=coll.created_at.isoformat(),
            updated_at=coll.updated_at.isoformat()
        )
        for coll in collections
    ]


@router.patch("/collections/{collection_id}", response_model=CollectionResponse)
async def update_collection(
    collection_id: str,
    request: UpdateCollectionRequest,
    current_user: UserInDB = Depends(get_current_user),
    batch_processor: BatchProcessor = Depends(get_batch_processor)
):
    """
    Update a document collection.

    - **add_document_ids**: List of document IDs to add to the collection
    - **remove_document_ids**: List of document IDs to remove from the collection
    - **name**: New name for the collection
    - **description**: New description for the collection
    """
    collection = await batch_processor.update_collection(
        collection_id=collection_id,
        user_id=current_user.id,
        add_document_ids=request.add_document_ids,
        remove_document_ids=request.remove_document_ids,
        name=request.name,
        description=request.description
    )

    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    return CollectionResponse(
        id=collection.id,
        user_id=collection.user_id,
        name=collection.name,
        description=collection.description,
        document_ids=collection.document_ids,
        document_count=collection.document_count,
        tags=collection.tags,
        project_name=collection.project_name,
        created_at=collection.created_at.isoformat(),
        updated_at=collection.updated_at.isoformat()
    )


@router.delete("/collections/{collection_id}", status_code=204)
async def delete_collection(
    collection_id: str,
    current_user: UserInDB = Depends(get_current_user),
    batch_processor: BatchProcessor = Depends(get_batch_processor)
):
    """
    Delete a document collection.

    Note: This only deletes the collection grouping, not the documents themselves.
    """
    success = await batch_processor.delete_collection(collection_id, current_user.id)

    if not success:
        raise HTTPException(status_code=404, detail="Collection not found")

    return None
