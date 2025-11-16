"""
Unit tests for multi-pass AI processing engine.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from bson import ObjectId

from app.services.processing_engine import ProcessingEngine
from app.models.template import TemplateSection, ProcessingStrategy, TemplateInDB
from app.services.pdf_processor import DocumentChunk


@pytest.fixture
def mock_db():
    """Mock MongoDB database."""
    return MagicMock()


@pytest.fixture
def processing_engine(mock_db):
    """Create processing engine with mocked dependencies."""
    return ProcessingEngine(mock_db)


@pytest.fixture
def sample_template():
    """Create sample template for testing."""
    return TemplateInDB(
        _id=ObjectId("507f1f77bcf86cd799439011"),
        name="Test Template",
        description="Test template",
        target_length="5 pages",
        category="general",
        sections=[
            TemplateSection(
                title="Introduction",
                guidance_prompt="Extract introduction and background",
                order=1,
                required=True
            ),
            TemplateSection(
                title="Findings",
                guidance_prompt="Summarize key findings",
                order=2,
                required=True
            )
        ],
        processing_strategy=ProcessingStrategy(
            approach="multi-pass",
            chunk_size=500,
            overlap=50,
            embedding_model="text-embedding-3-small",
            summarization_model="gpt-4o-mini",
            max_tokens_per_section=1500,
            temperature=0.3
        ),
        system_prompt="You are an expert analyst.",
        is_active=True,
        is_default=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        usage_count=0
    )


@pytest.fixture
def sample_chunks():
    """Create sample document chunks."""
    return [
        {
            "text": "This is chunk 1 about water resources.",
            "chunk_index": 0,
            "page_number": 1,
            "start_char": 0,
            "end_char": 40,
            "section_heading": "Introduction",
            "word_count": 7
        },
        {
            "text": "This is chunk 2 discussing technical aspects.",
            "chunk_index": 1,
            "page_number": 2,
            "start_char": 40,
            "end_char": 85,
            "section_heading": "Technical Analysis",
            "word_count": 7
        }
    ]


class TestProcessingEngineInitialization:
    """Test processing engine initialization."""

    def test_engine_initialization(self, processing_engine):
        """Test engine initializes with required services."""
        assert processing_engine.db is not None
        assert processing_engine.pdf_processor is not None
        assert processing_engine.embedding_service is not None
        assert processing_engine.openai_client is not None


class TestPass1Indexing:
    """Test Pass 1: Document indexing."""

    @pytest.mark.asyncio
    async def test_pass_1_index_document(self, processing_engine, sample_template):
        """Test document indexing creates chunks and embeddings."""
        document_id = "507f1f77bcf86cd799439011"
        file_path = "/path/to/test.pdf"

        # Mock PDF processor
        mock_process_result = {
            "extracted_data": {
                "total_pages": 10,
                "total_words": 5000,
                "total_chars": 30000
            },
            "chunks": [
                {
                    "text": "Test chunk",
                    "chunk_index": 0,
                    "page_number": 1,
                    "start_char": 0,
                    "end_char": 10,
                    "section_heading": None,
                    "word_count": 2
                }
            ],
            "total_chunks": 1
        }

        # Mock PDFProcessor class
        with patch('app.services.processing_engine.PDFProcessor') as MockProcessor:
            mock_instance = MockProcessor.return_value
            mock_instance.process_pdf.return_value = mock_process_result

            # Mock embedding service
            with patch.object(
                processing_engine.embedding_service,
                'generate_embeddings_for_chunks',
                return_value=["emb_id_1"]
            ) as mock_embed:
                result = await processing_engine._pass_1_index_document(
                    document_id, file_path, sample_template
                )

                assert result["total_pages"] == 10
                assert result["total_words"] == 5000
                assert result["total_chunks"] == 1
                assert result["embedding_count"] == 1
                mock_embed.assert_called_once()

    @pytest.mark.asyncio
    async def test_pass_1_uses_template_chunk_settings(self, processing_engine, sample_template):
        """Test that Pass 1 uses chunk settings from template."""
        document_id = "507f1f77bcf86cd799439011"
        file_path = "/path/to/test.pdf"

        mock_result = {
            "extracted_data": {"total_pages": 1, "total_words": 100, "total_chars": 500},
            "chunks": [],
            "total_chunks": 0
        }

        with patch.object(
            processing_engine.pdf_processor,
            'process_pdf',
            return_value=mock_result
        ):
            with patch.object(
                processing_engine.embedding_service,
                'generate_embeddings_for_chunks',
                return_value=[]
            ):
                # Check that PDFProcessor is created with template settings
                with patch('app.services.processing_engine.PDFProcessor') as MockProcessor:
                    MockProcessor.return_value.process_pdf.return_value = mock_result

                    await processing_engine._pass_1_index_document(
                        document_id, file_path, sample_template
                    )

                    # Verify PDFProcessor created with correct settings
                    MockProcessor.assert_called_once_with(
                        chunk_size=500,
                        overlap=50,
                        min_chunk_size=100
                    )


class TestPass2ThematicQuerying:
    """Test Pass 2: Thematic querying."""

    @pytest.mark.asyncio
    async def test_pass_2_query_relevant_chunks(self, processing_engine, sample_template):
        """Test querying relevant chunks using section guidance."""
        document_id = "507f1f77bcf86cd799439011"
        section = sample_template.sections[0]

        # Mock search results
        mock_results = [
            MagicMock(
                chunk_text="Relevant chunk 1",
                chunk_index=0,
                page_number=1,
                section_heading="Intro",
                word_count=10,
                similarity_score=0.85
            ),
            MagicMock(
                chunk_text="Relevant chunk 2",
                chunk_index=1,
                page_number=2,
                section_heading="Background",
                word_count=12,
                similarity_score=0.75
            )
        ]

        with patch.object(
            processing_engine.embedding_service,
            'search_similar_chunks',
            return_value=mock_results
        ) as mock_search:
            results = await processing_engine._pass_2_query_relevant_chunks(
                document_id, section, sample_template
            )

            assert len(results) == 2
            assert results[0]["chunk_text"] == "Relevant chunk 1"
            assert results[0]["similarity_score"] == 0.85
            assert results[1]["page_number"] == 2

            # Verify search query parameters
            call_args = mock_search.call_args[0][0]
            assert call_args.query_text == section.guidance_prompt
            assert call_args.document_id == document_id
            assert call_args.top_k == 20

    @pytest.mark.asyncio
    async def test_pass_2_handles_empty_results(self, processing_engine, sample_template):
        """Test handling when no relevant chunks found."""
        document_id = "507f1f77bcf86cd799439011"
        section = sample_template.sections[0]

        with patch.object(
            processing_engine.embedding_service,
            'search_similar_chunks',
            return_value=[]
        ):
            results = await processing_engine._pass_2_query_relevant_chunks(
                document_id, section, sample_template
            )

            assert results == []


class TestPass3Synthesis:
    """Test Pass 3: Section synthesis."""

    @pytest.mark.asyncio
    async def test_pass_3_synthesize_section(self, processing_engine, sample_template):
        """Test section synthesis with OpenAI."""
        section = sample_template.sections[0]
        relevant_chunks = [
            {
                "chunk_text": "Water resources are critical.",
                "chunk_index": 0,
                "page_number": 1,
                "section_heading": "Intro",
                "word_count": 5,
                "similarity_score": 0.9
            }
        ]

        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="Synthesized section content"))
        ]

        # Mock the async create method properly
        async def mock_create(*args, **kwargs):
            return mock_response

        with patch.object(
            processing_engine.openai_client.chat.completions,
            'create',
            side_effect=mock_create
        ) as mock_openai:
            result = await processing_engine._pass_3_synthesize_section(
                section, relevant_chunks, sample_template
            )

            assert result == "Synthesized section content"
            mock_openai.assert_called_once()

            # Verify OpenAI call parameters
            call_kwargs = mock_openai.call_args[1]
            assert call_kwargs["model"] == "gpt-4o-mini"
            assert call_kwargs["max_tokens"] == 1500
            assert call_kwargs["temperature"] == 0.3

    @pytest.mark.asyncio
    async def test_pass_3_handles_no_chunks(self, processing_engine, sample_template):
        """Test synthesis when no relevant chunks available."""
        section = sample_template.sections[0]
        relevant_chunks = []

        result = await processing_engine._pass_3_synthesize_section(
            section, relevant_chunks, sample_template
        )

        assert "No relevant content found" in result


class TestFullProcessing:
    """Test complete document processing."""

    @pytest.mark.asyncio
    async def test_process_document_success(
        self,
        processing_engine,
        sample_template,
        sample_chunks
    ):
        """Test successful document processing through all passes."""
        document_id = "507f1f77bcf86cd799439011"
        file_path = "/path/to/test.pdf"

        # Mock Pass 1
        mock_indexing = {
            "total_pages": 10,
            "total_words": 5000,
            "total_chunks": 10,
            "embedding_count": 10,
            "chunks": sample_chunks,
            "extracted_data": {"total_pages": 10, "total_words": 5000}
        }

        with patch.object(
            processing_engine,
            '_pass_1_index_document',
            return_value=mock_indexing
        ):
            # Mock Pass 2
            mock_chunks = [{"chunk_text": "Test", "page_number": 1, "similarity_score": 0.8}]
            with patch.object(
                processing_engine,
                '_pass_2_query_relevant_chunks',
                return_value=mock_chunks
            ):
                # Mock Pass 3
                with patch.object(
                    processing_engine,
                    '_pass_3_synthesize_section',
                    return_value="Section summary"
                ):
                    result = await processing_engine.process_document(
                        document_id, file_path, sample_template
                    )

                    assert result["status"] == "completed"
                    assert result["document_id"] == document_id
                    assert len(result["sections"]) == 2
                    assert result["metadata"]["total_pages"] == 10
                    assert "completed_at" in result

    @pytest.mark.asyncio
    async def test_process_document_with_progress_callback(
        self,
        processing_engine,
        sample_template
    ):
        """Test progress callback is called during processing."""
        document_id = "507f1f77bcf86cd799439011"
        file_path = "/path/to/test.pdf"

        progress_calls = []

        async def progress_callback(stage, message):
            progress_calls.append((stage, message))

        # Mock all passes
        with patch.object(
            processing_engine,
            '_pass_1_index_document',
            return_value={
                "total_pages": 1,
                "total_words": 100,
                "total_chunks": 1,
                "embedding_count": 1
            }
        ):
            with patch.object(
                processing_engine,
                '_pass_2_query_relevant_chunks',
                return_value=[]
            ):
                with patch.object(
                    processing_engine,
                    '_pass_3_synthesize_section',
                    return_value="Summary"
                ):
                    await processing_engine.process_document(
                        document_id,
                        file_path,
                        sample_template,
                        progress_callback=progress_callback
                    )

                    assert len(progress_calls) > 0
                    assert progress_calls[0][0] == "pass_1"

    @pytest.mark.asyncio
    async def test_process_document_handles_errors(
        self,
        processing_engine,
        sample_template
    ):
        """Test error handling during processing."""
        document_id = "507f1f77bcf86cd799439011"
        file_path = "/path/to/test.pdf"

        # Mock Pass 1 to raise error
        with patch.object(
            processing_engine,
            '_pass_1_index_document',
            side_effect=Exception("Processing failed")
        ):
            with pytest.raises(Exception, match="Processing failed"):
                await processing_engine.process_document(
                    document_id, file_path, sample_template
                )


class TestSectionProcessing:
    """Test individual section processing."""

    @pytest.mark.asyncio
    async def test_process_section(self, processing_engine, sample_template):
        """Test processing a single section."""
        document_id = "507f1f77bcf86cd799439011"
        section = sample_template.sections[0]
        indexing_result = {"total_pages": 10}

        mock_chunks = [
            {
                "chunk_text": "Test",
                "page_number": 1,
                "chunk_index": 0,
                "similarity_score": 0.8
            }
        ]

        with patch.object(
            processing_engine,
            '_pass_2_query_relevant_chunks',
            return_value=mock_chunks
        ):
            with patch.object(
                processing_engine,
                '_pass_3_synthesize_section',
                return_value="Section content"
            ):
                result = await processing_engine._process_section(
                    document_id, section, sample_template, indexing_result
                )

                assert result["title"] == "Introduction"
                assert result["content"] == "Section content"
                assert result["source_chunks"] == 1
                assert result["pages_referenced"] == [1]


class TestCostEstimation:
    """Test processing cost estimation."""

    @pytest.mark.asyncio
    async def test_estimate_processing_cost(self, processing_engine, sample_template):
        """Test cost estimation before processing."""
        file_path = "/path/to/test.pdf"

        # Mock PDF extraction
        mock_extracted = {
            "total_words": 10000,
            "total_pages": 20
        }

        # Mock PDFProcessor class for cost estimation
        with patch('app.services.processing_engine.PDFProcessor') as MockProcessor:
            mock_instance = MockProcessor.return_value
            mock_instance.extract_text_from_pdf.return_value = mock_extracted

            estimate = await processing_engine.estimate_processing_cost(
                file_path, sample_template
            )

            assert "total_words" in estimate
            assert estimate["total_words"] == 10000
            assert "costs" in estimate
            assert "total" in estimate["costs"]
            assert estimate["costs"]["currency"] == "USD"
            assert "estimated_duration_minutes" in estimate


class TestRegenerateSection:
    """Test section regeneration."""

    @pytest.mark.asyncio
    async def test_regenerate_section(self, processing_engine, sample_template):
        """Test regenerating a specific section."""
        document_id = "507f1f77bcf86cd799439011"
        section_title = "Introduction"
        indexing_result = {"total_pages": 10}

        with patch.object(
            processing_engine,
            '_process_section',
            return_value={"title": section_title, "content": "Regenerated"}
        ) as mock_process:
            result = await processing_engine.regenerate_section(
                document_id, section_title, sample_template, indexing_result
            )

            assert result["title"] == section_title
            assert result["content"] == "Regenerated"
            mock_process.assert_called_once()

    @pytest.mark.asyncio
    async def test_regenerate_nonexistent_section(
        self,
        processing_engine,
        sample_template
    ):
        """Test error when regenerating nonexistent section."""
        document_id = "507f1f77bcf86cd799439011"
        section_title = "Nonexistent Section"
        indexing_result = {}

        with pytest.raises(ValueError, match="not found in template"):
            await processing_engine.regenerate_section(
                document_id, section_title, sample_template, indexing_result
            )
