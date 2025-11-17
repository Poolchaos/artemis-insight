"""
Integration tests for document semantic search endpoint.
"""

import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock
from bson import ObjectId
from datetime import datetime

from app.models.user import UserInDB
from app.models.document import DocumentStatus


@pytest.mark.asyncio
class TestDocumentSearch:
    """Test semantic search functionality for documents."""

    @patch('app.services.embedding_service.EmbeddingService')
    async def test_search_document_success(
        self,
        mock_embedding_service_class,
        client: AsyncClient,
        test_user: UserInDB,
        access_token: str,
        test_db
    ):
        """Test successful document search with relevant results."""

        # Setup: Create a document with chunks
        document_id = ObjectId()
        await test_db.documents.insert_one({
            "_id": document_id,
            "user_id": ObjectId(test_user.id),
            "filename": "test_document.pdf",
            "file_path": f"documents/{test_user.id}/test.pdf",
            "file_size": 1000000,
            "mime_type": "application/pdf",
            "status": DocumentStatus.COMPLETED.value,
            "upload_date": datetime.utcnow(),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })

        # Create test chunks with embeddings
        query_embedding = [0.1] * 1536  # Simulated embedding
        chunks = [
            {
                "_id": ObjectId(),
                "document_id": document_id,
                "content": "The project costs are estimated at $2.5 million for capital expenditure.",
                "page_number": 10,
                "chunk_index": 0,
                "embedding": [0.11] * 1536  # High similarity to query
            },
            {
                "_id": ObjectId(),
                "document_id": document_id,
                "content": "Environmental impact assessment shows minimal negative effects.",
                "page_number": 25,
                "chunk_index": 1,
                "embedding": [0.5] * 1536  # Lower similarity
            },
            {
                "_id": ObjectId(),
                "document_id": document_id,
                "content": "The timeline for implementation is 18 months starting Q2 2024.",
                "page_number": 45,
                "chunk_index": 2,
                "embedding": [0.2] * 1536  # Medium similarity
            }
        ]

        await test_db.chunks.insert_many(chunks)

        # Mock embedding service - use AsyncMock for async methods
        mock_service = AsyncMock()
        mock_service.generate_embedding.return_value = query_embedding
        mock_embedding_service_class.return_value = mock_service

        # Configure client authentication
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Execute search
        response = await client.post(
            f"/api/documents/{str(document_id)}/search",
            json={
                "query": "What are the project costs?",
                "top_k": 3,
                "min_similarity": 0.7
            }
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()

        assert data["document_id"] == str(document_id)
        assert data["query"] == "What are the project costs?"
        assert len(data["results"]) > 0
        assert data["total_chunks_searched"] == 3
        assert data["search_duration_ms"] > 0

        # Verify results are sorted by similarity (highest first)
        similarities = [r["similarity_score"] for r in data["results"]]
        assert similarities == sorted(similarities, reverse=True)

        # Verify result structure
        first_result = data["results"][0]
        assert "chunk_id" in first_result
        assert "content" in first_result
        assert "page_number" in first_result
        assert "similarity_score" in first_result
        assert 0 <= first_result["similarity_score"] <= 1

        print(f"\n✅ Search completed in {data['search_duration_ms']:.2f}ms")
        print(f"   Found {len(data['results'])} results")
        print(f"   Top result: {first_result['content'][:80]}...")


    async def test_search_document_not_found(
        self,
        client: AsyncClient,
        test_user: UserInDB,
        access_token: str,
        test_db
    ):
        """Test search fails when document doesn't exist."""

        client.headers.update({"Authorization": f"Bearer {access_token}"})

        response = await client.post(
            f"/api/documents/{'0' * 24}/search",
            json={"query": "test query"}
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


    async def test_search_document_not_ready(
        self,
        client: AsyncClient,
        test_user: UserInDB,
        access_token: str,
        test_db
    ):
        """Test search fails when document is not processed yet."""

        # Create pending document
        document_id = ObjectId()
        await test_db.documents.insert_one({
            "_id": document_id,
            "user_id": ObjectId(test_user.id),
            "filename": "pending.pdf",
            "file_path": f"documents/{test_user.id}/pending.pdf",
            "file_size": 1000000,
            "mime_type": "application/pdf",
            "status": DocumentStatus.PROCESSING.value,
            "upload_date": datetime.utcnow(),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })

        client.headers.update({"Authorization": f"Bearer {access_token}"})

        response = await client.post(
            f"/api/documents/{str(document_id)}/search",
            json={"query": "test query"}
        )

        assert response.status_code == 400
        assert "not ready" in response.json()["detail"].lower()


    async def test_search_document_no_chunks(
        self,
        client: AsyncClient,
        test_user: UserInDB,
        access_token: str,
        test_db
    ):
        """Test search fails when document has no chunks."""

        # Create completed document without chunks
        document_id = ObjectId()
        await test_db.documents.insert_one({
            "_id": document_id,
            "user_id": ObjectId(test_user.id),
            "filename": "empty.pdf",
            "file_path": f"documents/{test_user.id}/empty.pdf",
            "file_size": 1000000,
            "mime_type": "application/pdf",
            "status": DocumentStatus.COMPLETED.value,
            "upload_date": datetime.utcnow(),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })

        client.headers.update({"Authorization": f"Bearer {access_token}"})

        response = await client.post(
            f"/api/documents/{str(document_id)}/search",
            json={"query": "test query"}
        )

        assert response.status_code == 404
        assert "no chunks" in response.json()["detail"].lower()


    @patch('app.services.embedding_service.EmbeddingService')
    async def test_search_with_min_similarity_filter(
        self,
        mock_embedding_service_class,
        client: AsyncClient,
        test_user: UserInDB,
        access_token: str,
        test_db
    ):
        """Test search respects minimum similarity threshold."""

        # Setup document and chunks
        document_id = ObjectId()
        await test_db.documents.insert_one({
            "_id": document_id,
            "user_id": ObjectId(test_user.id),
            "filename": "test.pdf",
            "file_path": f"documents/{test_user.id}/test.pdf",
            "file_size": 1000000,
            "mime_type": "application/pdf",
            "status": DocumentStatus.COMPLETED.value,
            "upload_date": datetime.utcnow(),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })

        # Create chunks with varying similarity
        # Use simple vectors to create predictable similarity scores
        query_embedding = [1.0] * 1536  # Unit vector in all dimensions
        chunks = [
            {
                "_id": ObjectId(),
                "document_id": document_id,
                "content": "High similarity content",
                "page_number": 1,
                "chunk_index": 0,
                "embedding": [1.0] * 1536  # Identical → similarity = 1.0
            },
            {
                "_id": ObjectId(),
                "document_id": document_id,
                "content": "Low similarity content",
                "page_number": 2,
                "chunk_index": 1,
                "embedding": [0.0] * 1536  # Orthogonal → similarity = 0.0
            }
        ]

        await test_db.chunks.insert_many(chunks)

        # Mock embedding service - use AsyncMock for async methods
        mock_service = AsyncMock()
        mock_service.generate_embedding.return_value = query_embedding
        mock_embedding_service_class.return_value = mock_service

        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Search with high minimum similarity threshold
        response = await client.post(
            f"/api/documents/{str(document_id)}/search",
            json={
                "query": "test query",
                "top_k": 10,
                "min_similarity": 0.95  # High threshold
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Should only return high similarity chunk
        assert len(data["results"]) == 1
        assert "High similarity" in data["results"][0]["content"]
        assert data["results"][0]["similarity_score"] >= 0.95


    async def test_search_unauthorized(
        self,
        client: AsyncClient,
        test_user: UserInDB,
        access_token: str,
        test_db
    ):
        """Test search fails for documents owned by other users."""

        # Create document owned by different user
        other_user_id = ObjectId()
        document_id = ObjectId()
        await test_db.documents.insert_one({
            "_id": document_id,
            "user_id": other_user_id,  # Different user
            "filename": "other.pdf",
            "file_path": f"documents/{other_user_id}/other.pdf",
            "file_size": 1000000,
            "mime_type": "application/pdf",
            "status": DocumentStatus.COMPLETED.value,
            "upload_date": datetime.utcnow(),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })

        client.headers.update({"Authorization": f"Bearer {access_token}"})

        response = await client.post(
            f"/api/documents/{str(document_id)}/search",
            json={"query": "test query"}
        )

        # Should not find document (filtered by user_id)
        assert response.status_code == 404


    @patch('app.services.embedding_service.EmbeddingService')
    async def test_search_with_top_k_limit(
        self,
        mock_embedding_service_class,
        client: AsyncClient,
        test_user: UserInDB,
        access_token: str,
        test_db
    ):
        """Test search respects top_k parameter."""

        # Setup document with many chunks
        document_id = ObjectId()
        await test_db.documents.insert_one({
            "_id": document_id,
            "user_id": ObjectId(test_user.id),
            "filename": "test.pdf",
            "file_path": f"documents/{test_user.id}/test.pdf",
            "file_size": 1000000,
            "mime_type": "application/pdf",
            "status": DocumentStatus.COMPLETED.value,
            "upload_date": datetime.utcnow(),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })

        # Create 10 chunks, all with good similarity
        query_embedding = [0.1] * 1536
        chunks = [
            {
                "_id": ObjectId(),
                "document_id": document_id,
                "content": f"Content chunk {i}",
                "page_number": i + 1,
                "chunk_index": i,
                "embedding": [0.11 + i * 0.01] * 1536  # Varying similarity
            }
            for i in range(10)
        ]

        await test_db.chunks.insert_many(chunks)

        # Mock embedding service - use AsyncMock for async methods
        mock_service = AsyncMock()
        mock_service.generate_embedding.return_value = query_embedding
        mock_embedding_service_class.return_value = mock_service

        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Search with top_k=3
        response = await client.post(
            f"/api/documents/{str(document_id)}/search",
            json={
                "query": "test query",
                "top_k": 3,
                "min_similarity": 0.0
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Should return exactly 3 results (top_k limit)
        assert len(data["results"]) == 3
        assert data["total_chunks_searched"] == 10

        print(f"\n✅ Top-k filter working: returned {len(data['results'])}/10 chunks")
