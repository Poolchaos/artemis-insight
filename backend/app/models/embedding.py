"""
Embedding model for storing document vectors for semantic search.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator

from app.models.user import PyObjectId


class EmbeddingBase(BaseModel):
    """Base embedding schema."""
    chunk_text: str = Field(..., min_length=1, description="Text chunk that was embedded")
    embedding_vector: List[float] = Field(..., description="Vector embedding of the chunk")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata about the chunk")

    @field_validator('embedding_vector')
    @classmethod
    def validate_embedding_vector(cls, v: List[float]) -> List[float]:
        """Validate embedding vector is not empty and has reasonable dimensions."""
        if not v:
            raise ValueError("Embedding vector cannot be empty")
        if len(v) > 10000:  # Sanity check for vector dimensions
            raise ValueError("Embedding vector dimensions exceed maximum limit")
        return v


class EmbeddingCreate(EmbeddingBase):
    """Schema for creating a new embedding."""
    document_id: str = Field(..., description="Associated document ID")
    chunk_id: int = Field(..., ge=0, description="Chunk sequence number within document")

    @field_validator('document_id')
    @classmethod
    def validate_document_id(cls, v: str) -> str:
        """Validate document_id is a valid ObjectId."""
        PyObjectId.validate(v, None)
        return v


class EmbeddingInDB(EmbeddingBase):
    """Embedding schema as stored in database."""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    document_id: PyObjectId = Field(..., description="Associated document ID")
    chunk_id: int = Field(..., ge=0, description="Chunk sequence number")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {PyObjectId: str, datetime: lambda v: v.isoformat()}


class EmbeddingResponse(BaseModel):
    """Embedding schema for API responses."""
    id: str = Field(..., description="Embedding ID")
    document_id: str = Field(..., description="Document ID")
    chunk_id: int = Field(..., description="Chunk sequence number")
    chunk_text: str
    embedding_vector: List[float]
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class EmbeddingSearchQuery(BaseModel):
    """Schema for embedding similarity search queries."""
    query_vector: List[float] = Field(..., description="Query vector for similarity search")
    top_k: int = Field(default=10, ge=1, le=100, description="Number of results to return")
    document_ids: Optional[List[str]] = Field(default=None, description="Optional filter by document IDs")
    min_similarity: Optional[float] = Field(default=None, ge=0, le=1, description="Minimum similarity threshold")

    @field_validator('document_ids')
    @classmethod
    def validate_document_ids(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate document IDs are valid ObjectIds."""
        if v is not None:
            for doc_id in v:
                PyObjectId.validate(doc_id, None)
        return v


class EmbeddingSearchResult(BaseModel):
    """Schema for embedding search results."""
    embedding: EmbeddingResponse
    similarity_score: float = Field(..., ge=0, le=1, description="Cosine similarity score")

    class Config:
        from_attributes = True
