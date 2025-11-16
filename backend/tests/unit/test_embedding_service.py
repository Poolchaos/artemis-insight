"""
Unit tests for embedding service.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.embedding_service import EmbeddingService
from app.services.pdf_processor import DocumentChunk
from app.models.embedding import EmbeddingSearchQuery


@pytest.fixture
def mock_db():
    """Mock MongoDB database."""
    db = MagicMock()
    db.embeddings = AsyncMock()
    return db


@pytest.fixture
def embedding_service(mock_db):
    """Create embedding service with mocked database."""
    return EmbeddingService(mock_db)


@pytest.fixture
def sample_chunks():
    """Create sample document chunks for testing."""
    return [
        DocumentChunk(
            text="This is the first test chunk about water resources.",
            chunk_index=0,
            page_number=1,
            start_char=0,
            end_char=51,
            section_heading="Introduction",
            word_count=9
        ),
        DocumentChunk(
            text="This is the second chunk discussing technical aspects of the project.",
            chunk_index=1,
            page_number=2,
            start_char=51,
            end_char=120,
            section_heading="Technical Analysis",
            word_count=11
        ),
        DocumentChunk(
            text="The third chunk covers economic considerations and cost estimates.",
            chunk_index=2,
            page_number=3,
            start_char=120,
            end_char=186,
            section_heading="Economic Assessment",
            word_count=10
        )
    ]


class TestEmbeddingServiceInitialization:
    """Test embedding service initialization."""

    def test_service_initialization(self, embedding_service):
        """Test service initializes correctly."""
        assert embedding_service.model == "text-embedding-3-small"
        assert embedding_service.batch_size == 100
        assert embedding_service.db is not None
        assert embedding_service.collection is not None


class TestGenerateEmbedding:
    """Test single embedding generation."""

    @pytest.mark.asyncio
    async def test_generate_embedding_success(self, embedding_service):
        """Test generating a single embedding."""
        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1] * 1536)]

        with patch.object(embedding_service.client.embeddings, 'create', return_value=mock_response):
            embedding = await embedding_service.generate_embedding("Test text")

            assert isinstance(embedding, list)
            assert len(embedding) == 1536
            assert all(isinstance(x, float) for x in embedding)

    @pytest.mark.asyncio
    async def test_generate_embedding_with_empty_text(self, embedding_service):
        """Test generating embedding with empty text."""
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.0] * 1536)]

        with patch.object(embedding_service.client.embeddings, 'create', return_value=mock_response):
            embedding = await embedding_service.generate_embedding("")

            assert len(embedding) == 1536


class TestGenerateEmbeddingsBatch:
    """Test batch embedding generation."""

    @pytest.mark.asyncio
    async def test_generate_batch_success(self, embedding_service):
        """Test generating embeddings for multiple texts."""
        texts = ["Text one", "Text two", "Text three"]

        mock_response = MagicMock()
        mock_response.data = [
            MagicMock(embedding=[0.1] * 1536),
            MagicMock(embedding=[0.2] * 1536),
            MagicMock(embedding=[0.3] * 1536)
        ]

        with patch.object(embedding_service.client.embeddings, 'create', return_value=mock_response):
            embeddings = await embedding_service.generate_embeddings_batch(texts)

            assert len(embeddings) == 3
            assert all(len(emb) == 1536 for emb in embeddings)

    @pytest.mark.asyncio
    async def test_generate_batch_exceeds_limit(self, embedding_service):
        """Test error when batch size exceeds limit."""
        texts = ["Text"] * 101  # More than batch_size of 100

        with pytest.raises(ValueError, match="exceeds maximum"):
            await embedding_service.generate_embeddings_batch(texts)

    @pytest.mark.asyncio
    async def test_generate_batch_empty_list(self, embedding_service):
        """Test generating embeddings for empty list."""
        mock_response = MagicMock()
        mock_response.data = []

        with patch.object(embedding_service.client.embeddings, 'create', return_value=mock_response):
            embeddings = await embedding_service.generate_embeddings_batch([])

            assert embeddings == []


class TestGenerateEmbeddingsForChunks:
    """Test embedding generation for document chunks."""

    @pytest.mark.asyncio
    async def test_generate_for_chunks_success(self, embedding_service, sample_chunks, mock_db):
        """Test generating embeddings for document chunks."""
        document_id = "507f1f77bcf86cd799439011"

        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1] * 1536) for _ in sample_chunks]

        # Mock database insert
        mock_db.embeddings.insert_many = AsyncMock(
            return_value=MagicMock(inserted_ids=["id1", "id2", "id3"])
        )

        with patch.object(embedding_service.client.embeddings, 'create', return_value=mock_response):
            embedding_ids = await embedding_service.generate_embeddings_for_chunks(
                sample_chunks,
                document_id
            )

            assert len(embedding_ids) == 3
            mock_db.embeddings.insert_many.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_for_chunks_empty_list(self, embedding_service):
        """Test error when chunks list is empty."""
        with pytest.raises(ValueError, match="empty chunks list"):
            await embedding_service.generate_embeddings_for_chunks([], "doc_id")

    @pytest.mark.asyncio
    async def test_generate_for_chunks_batching(self, embedding_service, mock_db):
        """Test that large chunk lists are processed in batches."""
        # Create 150 chunks (should be split into 2 batches)
        chunks = [
            DocumentChunk(
                text=f"Chunk {i}",
                chunk_index=i,
                page_number=1,
                start_char=i * 10,
                end_char=(i + 1) * 10
            )
            for i in range(150)
        ]

        document_id = "507f1f77bcf86cd799439011"

        # Mock OpenAI responses for 2 batches
        mock_response1 = MagicMock()
        mock_response1.data = [MagicMock(embedding=[0.1] * 1536) for _ in range(100)]

        mock_response2 = MagicMock()
        mock_response2.data = [MagicMock(embedding=[0.2] * 1536) for _ in range(50)]

        # Mock database inserts
        mock_db.embeddings.insert_many = AsyncMock(
            side_effect=[
                MagicMock(inserted_ids=["id"] * 100),
                MagicMock(inserted_ids=["id"] * 50)
            ]
        )

        with patch.object(
            embedding_service.client.embeddings,
            'create',
            side_effect=[mock_response1, mock_response2]
        ):
            embedding_ids = await embedding_service.generate_embeddings_for_chunks(
                chunks,
                document_id
            )

            assert len(embedding_ids) == 150
            assert mock_db.embeddings.insert_many.call_count == 2


class TestCosineSimilarity:
    """Test cosine similarity calculation."""

    def test_cosine_similarity_identical_vectors(self, embedding_service):
        """Test similarity of identical vectors."""
        vec = [1.0, 2.0, 3.0]
        similarity = embedding_service._cosine_similarity(vec, vec)

        assert similarity == pytest.approx(1.0, abs=0.01)

    def test_cosine_similarity_orthogonal_vectors(self, embedding_service):
        """Test similarity of orthogonal vectors."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        similarity = embedding_service._cosine_similarity(vec1, vec2)

        assert similarity == pytest.approx(0.0, abs=0.01)

    def test_cosine_similarity_opposite_vectors(self, embedding_service):
        """Test similarity of opposite vectors."""
        vec1 = [1.0, 0.0]
        vec2 = [-1.0, 0.0]
        similarity = embedding_service._cosine_similarity(vec1, vec2)

        # Cosine similarity clamped to [0, 1], so -1 becomes 0
        assert similarity == pytest.approx(0.0, abs=0.01)

    def test_cosine_similarity_zero_vector(self, embedding_service):
        """Test similarity with zero vector."""
        vec1 = [0.0, 0.0, 0.0]
        vec2 = [1.0, 2.0, 3.0]
        similarity = embedding_service._cosine_similarity(vec1, vec2)

        assert similarity == 0.0


class TestSearchSimilarChunks:
    """Test semantic search functionality."""

    @pytest.mark.asyncio
    async def test_search_with_query_vector(self, embedding_service, mock_db):
        """Test searching with pre-computed query vector."""
        query_vector = [0.1] * 1536

        # Mock database query
        mock_cursor = AsyncMock()
        mock_cursor.to_list = AsyncMock(return_value=[
            {
                "_id": "emb1",
                "document_id": "doc1",
                "chunk_index": 0,
                "chunk_text": "Test chunk",
                "embedding_vector": [0.1] * 1536,
                "page_number": 1,
                "section_heading": "Intro",
                "word_count": 10
            }
        ])

        mock_db.embeddings.find = MagicMock(return_value=mock_cursor)

        query = EmbeddingSearchQuery(
            query_vector=query_vector,
            top_k=10,
            min_similarity=0.5
        )

        results = await embedding_service.search_similar_chunks(query)

        assert len(results) <= 10
        assert all(hasattr(r, 'similarity_score') for r in results)

    @pytest.mark.asyncio
    async def test_search_with_query_text(self, embedding_service, mock_db):
        """Test searching with query text."""
        # Mock embedding generation
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1] * 1536)]

        # Mock database query
        mock_cursor = AsyncMock()
        mock_cursor.to_list = AsyncMock(return_value=[])

        mock_db.embeddings.find = MagicMock(return_value=mock_cursor)

        with patch.object(embedding_service.client.embeddings, 'create', return_value=mock_response):
            query = EmbeddingSearchQuery(
                query_text="test query",
                top_k=5
            )

            results = await embedding_service.search_similar_chunks(query)

            assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_filters_by_document_id(self, embedding_service, mock_db):
        """Test search filtering by document ID."""
        query_vector = [0.1] * 1536
        document_id = "507f1f77bcf86cd799439011"

        mock_cursor = AsyncMock()
        mock_cursor.to_list = AsyncMock(return_value=[])

        mock_db.embeddings.find = MagicMock(return_value=mock_cursor)

        query = EmbeddingSearchQuery(
            query_vector=query_vector,
            document_id=document_id,
            top_k=10
        )

        await embedding_service.search_similar_chunks(query)

        # Verify find was called with document_id filter
        call_args = mock_db.embeddings.find.call_args[0][0]
        assert "document_id" in call_args


class TestEmbeddingCRUD:
    """Test CRUD operations for embeddings."""

    @pytest.mark.asyncio
    async def test_get_embeddings_for_document(self, embedding_service, mock_db):
        """Test retrieving embeddings for a document."""
        document_id = "507f1f77bcf86cd799439011"

        mock_cursor = AsyncMock()
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.skip = MagicMock(return_value=mock_cursor)
        mock_cursor.limit = MagicMock(return_value=mock_cursor)
        mock_cursor.to_list = AsyncMock(return_value=[
            {
                "_id": "emb1",
                "document_id": document_id,
                "chunk_index": 0
            }
        ])

        mock_db.embeddings.find = MagicMock(return_value=mock_cursor)

        embeddings = await embedding_service.get_embeddings_for_document(document_id)

        assert len(embeddings) > 0
        assert embeddings[0]["document_id"] == document_id

    @pytest.mark.asyncio
    async def test_delete_embeddings_for_document(self, embedding_service, mock_db):
        """Test deleting all embeddings for a document."""
        document_id = "507f1f77bcf86cd799439011"

        mock_db.embeddings.delete_many = AsyncMock(
            return_value=MagicMock(deleted_count=5)
        )

        count = await embedding_service.delete_embeddings_for_document(document_id)

        assert count == 5
        mock_db.embeddings.delete_many.assert_called_once()

    @pytest.mark.asyncio
    async def test_count_embeddings_all(self, embedding_service, mock_db):
        """Test counting all embeddings."""
        mock_db.embeddings.count_documents = AsyncMock(return_value=100)

        count = await embedding_service.count_embeddings()

        assert count == 100

    @pytest.mark.asyncio
    async def test_count_embeddings_for_document(self, embedding_service, mock_db):
        """Test counting embeddings for specific document."""
        document_id = "507f1f77bcf86cd799439011"

        mock_db.embeddings.count_documents = AsyncMock(return_value=15)

        count = await embedding_service.count_embeddings(document_id)

        assert count == 15
