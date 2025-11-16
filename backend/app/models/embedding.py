"""
Embedding model for storing document chunk vectors for semantic search.

Embeddings are generated from PDF document chunks and used for:
- Semantic search within documents
- Multi-pass AI processing (Pass 2: thematic querying)
- Section-specific content retrieval using template guidance prompts
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator
from bson import ObjectId

from app.models.user import PyObjectId


class EmbeddingBase(BaseModel):
    """Base embedding schema."""

    document_id: str = Field(..., description="ID of source document")
    chunk_index: int = Field(..., ge=0, description="Index of chunk within document (from PDFProcessor)")
    chunk_text: str = Field(..., min_length=1, description="Text chunk that was embedded")
    embedding_vector: List[float] = Field(..., description="1536-dimensional embedding from text-embedding-3-small")

    # Metadata from PDFProcessor's DocumentChunk
    page_number: int = Field(..., description="Page number in source document")
    section_heading: Optional[str] = Field(None, description="Section heading if detected")
    word_count: int = Field(..., description="Number of words in chunk")
    start_char: int = Field(..., description="Start character position in full document")
    end_char: int = Field(..., description="End character position in full document")

    model: str = Field(default="text-embedding-3-small", description="OpenAI embedding model used")

    @field_validator('embedding_vector')
    @classmethod
    def validate_embedding_vector(cls, v: List[float]) -> List[float]:
        """Validate embedding vector dimensions (text-embedding-3-small = 1536 dimensions)."""
        if not v:
            raise ValueError("Embedding vector cannot be empty")
        if len(v) != 1536:
            raise ValueError(f"Expected 1536 dimensions for text-embedding-3-small, got {len(v)}")
        return v


class EmbeddingCreate(EmbeddingBase):
    """Schema for creating a new embedding."""

    @field_validator('document_id')
    @classmethod
    def validate_document_id(cls, v: str) -> str:
        """Validate document_id is a valid ObjectId."""
        try:
            ObjectId(v)
        except Exception:
            raise ValueError(f"Invalid document_id: {v}")
        return v


class EmbeddingInDB(EmbeddingBase):
    """Embedding schema as stored in database."""

    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    document_id: PyObjectId = Field(..., description="Associated document ID")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {PyObjectId: str, datetime: lambda v: v.isoformat()}


class EmbeddingResponse(BaseModel):
    """Embedding schema for API responses (without embedding vector for efficiency)."""

    id: str = Field(..., description="Embedding ID")
    document_id: str = Field(..., description="Document ID")
    chunk_index: int = Field(..., description="Chunk index")
    page_number: int
    section_heading: Optional[str]
    word_count: int
    model: str
    created_at: datetime

    # Embedding vector omitted by default (1536 floats = large payload)
    # Can be retrieved separately if needed

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class EmbeddingSearchQuery(BaseModel):
    """Schema for embedding similarity search queries."""

    query_text: Optional[str] = Field(None, description="Text to embed and search (alternative to query_vector)")
    query_vector: Optional[List[float]] = Field(None, description="Pre-computed query vector for similarity search")
    top_k: int = Field(default=10, ge=1, le=100, description="Number of results to return")
    document_id: Optional[str] = Field(None, description="Filter by specific document")
    min_similarity: Optional[float] = Field(default=0.5, ge=0, le=1, description="Minimum similarity threshold")

    @field_validator('query_vector')
    @classmethod
    def validate_query_vector(cls, v: Optional[List[float]]) -> Optional[List[float]]:
        """Validate query vector dimensions if provided."""
        if v is not None and len(v) != 1536:
            raise ValueError(f"Query vector must be 1536 dimensions, got {len(v)}")
        return v

    @field_validator('document_id')
    @classmethod
    def validate_document_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate document_id is valid ObjectId if provided."""
        if v is not None:
            try:
                ObjectId(v)
            except Exception:
                raise ValueError(f"Invalid document_id: {v}")
        return v

    def model_post_init(self, __context):
        """Ensure either query_text or query_vector is provided."""
        if self.query_text is None and self.query_vector is None:
            raise ValueError("Either query_text or query_vector must be provided")


class SimilarChunk(BaseModel):
    """Represents a chunk similar to a query."""

    document_id: str
    chunk_index: int
    page_number: int
    section_heading: Optional[str]
    word_count: int
    similarity_score: float = Field(..., ge=0, le=1, description="Cosine similarity (0-1)")
    chunk_text: Optional[str] = Field(None, description="Actual chunk text")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class EmbeddingSearchResult(BaseModel):
    """Schema for embedding search results with similarity scores."""

    embedding_id: str
    document_id: str
    chunk_index: int
    chunk_text: str
    page_number: int
    section_heading: Optional[str]
    word_count: int
    similarity_score: float = Field(..., ge=0, le=1, description="Cosine similarity score")

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat()}

