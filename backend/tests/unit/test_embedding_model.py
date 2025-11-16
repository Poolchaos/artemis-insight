"""
Unit tests for embedding model.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError
from bson import ObjectId

from app.models.embedding import (
    EmbeddingBase,
    EmbeddingCreate,
    EmbeddingInDB,
    EmbeddingResponse,
    EmbeddingSearchQuery,
    EmbeddingSearchResult
)


def test_embedding_base_valid():
    """Test valid embedding base creation."""
    embedding = EmbeddingBase(
        chunk_text="This is a text chunk",
        embedding_vector=[0.1, 0.2, 0.3, 0.4],
        metadata={"page": 1}
    )
    assert embedding.chunk_text == "This is a text chunk"
    assert len(embedding.embedding_vector) == 4
    assert embedding.metadata["page"] == 1


def test_embedding_base_empty_vector():
    """Test embedding with empty vector."""
    with pytest.raises(ValidationError) as exc_info:
        EmbeddingBase(
            chunk_text="Text",
            embedding_vector=[]
        )
    assert "cannot be empty" in str(exc_info.value)


def test_embedding_base_vector_too_large():
    """Test embedding with excessively large vector."""
    with pytest.raises(ValidationError) as exc_info:
        EmbeddingBase(
            chunk_text="Text",
            embedding_vector=[0.1] * 10001
        )
    assert "exceed maximum limit" in str(exc_info.value)


def test_embedding_create_valid():
    """Test valid embedding creation."""
    embedding = EmbeddingCreate(
        document_id=str(ObjectId()),
        chunk_id=0,
        chunk_text="First chunk",
        embedding_vector=[0.5, 0.6, 0.7]
    )
    assert embedding.chunk_id == 0
    assert len(embedding.embedding_vector) == 3


def test_embedding_create_invalid_document_id():
    """Test embedding create with invalid document ID."""
    with pytest.raises(ValidationError) as exc_info:
        EmbeddingCreate(
            document_id="invalid",
            chunk_id=0,
            chunk_text="Text",
            embedding_vector=[0.1]
        )
    assert "Invalid ObjectId" in str(exc_info.value)


def test_embedding_create_negative_chunk_id():
    """Test embedding with negative chunk ID."""
    with pytest.raises(ValidationError) as exc_info:
        EmbeddingCreate(
            document_id=str(ObjectId()),
            chunk_id=-1,
            chunk_text="Text",
            embedding_vector=[0.1]
        )
    assert "greater than or equal to 0" in str(exc_info.value)


def test_embedding_in_db():
    """Test embedding in database schema."""
    embedding = EmbeddingInDB(
        document_id=ObjectId(),
        chunk_id=5,
        chunk_text="Chunk text",
        embedding_vector=[0.1, 0.2]
    )
    assert embedding.id is not None
    assert isinstance(embedding.created_at, datetime)
    assert embedding.chunk_id == 5


def test_embedding_response():
    """Test embedding API response schema."""
    response = EmbeddingResponse(
        id=str(ObjectId()),
        document_id=str(ObjectId()),
        chunk_id=10,
        chunk_text="Response text",
        embedding_vector=[0.3, 0.4],
        created_at=datetime.utcnow()
    )
    assert response.chunk_id == 10
    assert len(response.embedding_vector) == 2


def test_embedding_search_query_valid():
    """Test valid embedding search query."""
    query = EmbeddingSearchQuery(
        query_vector=[0.1, 0.2, 0.3],
        top_k=5,
        min_similarity=0.8
    )
    assert len(query.query_vector) == 3
    assert query.top_k == 5
    assert query.min_similarity == 0.8


def test_embedding_search_query_with_filters():
    """Test search query with document ID filters."""
    doc_ids = [str(ObjectId()), str(ObjectId())]
    query = EmbeddingSearchQuery(
        query_vector=[0.1],
        document_ids=doc_ids
    )
    assert len(query.document_ids) == 2


def test_embedding_search_query_invalid_top_k():
    """Test search query with invalid top_k."""
    with pytest.raises(ValidationError) as exc_info:
        EmbeddingSearchQuery(
            query_vector=[0.1],
            top_k=0
        )
    assert "greater than or equal to 1" in str(exc_info.value)


def test_embedding_search_query_top_k_too_large():
    """Test search query with top_k exceeding limit."""
    with pytest.raises(ValidationError) as exc_info:
        EmbeddingSearchQuery(
            query_vector=[0.1],
            top_k=101
        )
    assert "less than or equal to 100" in str(exc_info.value)


def test_embedding_search_query_invalid_document_ids():
    """Test search query with invalid document IDs."""
    with pytest.raises(ValidationError) as exc_info:
        EmbeddingSearchQuery(
            query_vector=[0.1],
            document_ids=["invalid-id"]
        )
    assert "Invalid ObjectId" in str(exc_info.value)


def test_embedding_search_result():
    """Test embedding search result."""
    embedding_resp = EmbeddingResponse(
        id=str(ObjectId()),
        document_id=str(ObjectId()),
        chunk_id=1,
        chunk_text="Result text",
        embedding_vector=[0.5],
        created_at=datetime.utcnow()
    )
    result = EmbeddingSearchResult(
        embedding=embedding_resp,
        similarity_score=0.92
    )
    assert result.similarity_score == 0.92
    assert result.embedding.chunk_text == "Result text"
