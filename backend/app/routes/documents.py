"""
Document management routes.
"""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_db
from app.models.user import UserInDB
from app.models.document import (
    DocumentCreate,
    DocumentResponse,
    DocumentStatus,
    DocumentUpdate,
    SearchQuery,
    SearchResponse,
    SearchResult
)
from app.middleware.auth import get_current_user
from app.services.document_service import DocumentService
from app.services.minio_service import minio_service


router = APIRouter(prefix="/api/documents", tags=["documents"])


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


@router.post("/{document_id}/search", response_model=SearchResponse)
async def search_document(
    document_id: str,
    search_query: SearchQuery,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Search document using natural language query.

    Uses semantic search with embeddings to find relevant passages:
    - Converts query to embedding vector
    - Compares with all document chunk embeddings
    - Returns top-k most similar chunks with scores

    **Example queries:**
    - "What are the project costs?"
    - "Describe the environmental impact"
    - "What is the timeline for implementation?"

    **Response includes:**
    - Matching text passages
    - Page numbers
    - Similarity scores (0-1)
    - Search execution time
    """
    import time
    from app.services.embedding_service import EmbeddingService, cosine_similarity

    start_time = time.time()

    # Verify document exists and belongs to user
    document_service = DocumentService(db)
    document = await document_service.get_document_by_user(document_id, str(current_user.id))

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Verify document processing is complete
    if document.status != DocumentStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Document is not ready for search. Status: {document.status.value}"
        )

    # Get all chunks for this document
    chunks_collection = db.chunks
    chunks_cursor = chunks_collection.find({"document_id": document.id})
    chunks = await chunks_cursor.to_list(length=None)

    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No chunks found for this document. Document may not be properly processed."
        )

    # Generate query embedding
    embedding_service = EmbeddingService()
    try:
        query_embedding = await embedding_service.generate_embedding(search_query.query)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate query embedding: {str(e)}"
        )

    # Calculate similarity scores for all chunks
    scored_chunks = []
    for chunk in chunks:
        if "embedding" not in chunk or not chunk["embedding"]:
            continue

        similarity = cosine_similarity(query_embedding, chunk["embedding"])

        # Filter by minimum similarity threshold
        if similarity >= search_query.min_similarity:
            scored_chunks.append({
                "chunk": chunk,
                "similarity": similarity
            })

    # Sort by similarity score (highest first)
    scored_chunks.sort(key=lambda x: x["similarity"], reverse=True)

    # Take top-k results
    top_chunks = scored_chunks[:search_query.top_k]

    # Format results
    search_results = [
        SearchResult(
            chunk_id=str(item["chunk"]["_id"]),
            content=item["chunk"]["content"],
            page_number=item["chunk"]["page_number"],
            similarity_score=round(item["similarity"], 4),
            metadata={
                "chunk_index": item["chunk"].get("chunk_index"),
                "word_count": len(item["chunk"]["content"].split())
            }
        )
        for item in top_chunks
    ]

    end_time = time.time()
    search_duration_ms = (end_time - start_time) * 1000

    return SearchResponse(
        document_id=document_id,
        query=search_query.query,
        results=search_results,
        total_chunks_searched=len(chunks),
        search_duration_ms=round(search_duration_ms, 2)
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

