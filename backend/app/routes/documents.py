"""
Document management routes.
"""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_db
from app.models.user import UserInDB
from app.models.document import DocumentCreate, DocumentResponse, DocumentStatus, DocumentUpdate
from app.middleware.auth import get_current_user
from app.services.document_service import DocumentService
from app.services.minio_service import minio_service


router = APIRouter(prefix="/documents", tags=["documents"])


# File validation constants
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_MIME_TYPES = ["application/pdf"]


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Upload a PDF document.

    - Validates file type and size
    - Stores file in MinIO
    - Creates document record in MongoDB
    """
    # Validate file type
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Only PDF files are allowed."
        )

    # Read file content
    content = await file.read()
    file_size = len(content)

    # Validate file size
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum limit of {MAX_FILE_SIZE / (1024 * 1024)}MB"
        )

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is empty"
        )

    # Generate unique file path
    file_extension = file.filename.split('.')[-1] if '.' in file.filename else 'pdf'
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = f"documents/{str(current_user.id)}/{unique_filename}"

    # Upload to MinIO
    try:
        from io import BytesIO
        file_obj = BytesIO(content)
        minio_service.upload_file(
            file_obj,
            file_path,
            content_type=file.content_type
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(e)}"
        )

    # Create document record
    document_data = DocumentCreate(
        user_id=str(current_user.id),
        filename=file.filename,
        file_path=file_path,
        file_size=file_size,
        mime_type=file.content_type,
        status=DocumentStatus.PENDING
    )

    document_service = DocumentService(db)
    document = await document_service.create_document(document_data, file_path)

    # Convert to response model
    return DocumentResponse(
        id=str(document.id),
        user_id=str(document.user_id),
        filename=document.filename,
        file_path=document.file_path,
        file_size=document.file_size,
        mime_type=document.mime_type,
        status=document.status,
        processing_metadata=document.processing_metadata,
        upload_date=document.upload_date,
        created_at=document.created_at,
        updated_at=document.updated_at
    )


@router.get("", response_model=List[DocumentResponse])
async def list_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    status: Optional[DocumentStatus] = None,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    List user's documents.

    - Supports pagination
    - Optional status filter
    """
    document_service = DocumentService(db)
    documents = await document_service.list_user_documents(
        str(current_user.id),
        skip=skip,
        limit=limit,
        status=status
    )

    return [
        DocumentResponse(
            id=str(doc.id),
            user_id=str(doc.user_id),
            filename=doc.filename,
            file_path=doc.file_path,
            file_size=doc.file_size,
            mime_type=doc.mime_type,
            status=doc.status,
            processing_metadata=doc.processing_metadata,
            upload_date=doc.upload_date,
            created_at=doc.created_at,
            updated_at=doc.updated_at
        )
        for doc in documents
    ]


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Get a specific document.

    - Returns 404 if document not found or doesn't belong to user
    """
    document_service = DocumentService(db)
    document = await document_service.get_document_by_user(document_id, str(current_user.id))

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    return DocumentResponse(
        id=str(document.id),
        user_id=str(document.user_id),
        filename=document.filename,
        file_path=document.file_path,
        file_size=document.file_size,
        mime_type=document.mime_type,
        status=document.status,
        processing_metadata=document.processing_metadata,
        upload_date=document.upload_date,
        created_at=document.created_at,
        updated_at=document.updated_at
    )


@router.get("/{document_id}/download")
async def download_document(
    document_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Get a presigned URL for downloading a document.

    - Returns a temporary URL that expires in 1 hour
    """
    document_service = DocumentService(db)
    document = await document_service.get_document_by_user(document_id, str(current_user.id))

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    try:
        presigned_url = minio_service.get_presigned_url(document.file_path)
        return {"download_url": presigned_url}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate download URL: {str(e)}"
        )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Delete a document.

    - Removes file from MinIO
    - Deletes document record from MongoDB
    """
    document_service = DocumentService(db)
    deleted = await document_service.delete_document(document_id, str(current_user.id))

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    return None
