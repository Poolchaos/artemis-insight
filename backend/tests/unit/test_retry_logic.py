"""
Unit tests for OpenAI retry logic and timeout handling in ProcessingEngine.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from bson import ObjectId
from openai import APITimeoutError, RateLimitError, APIError
import httpx

from app.services.processing_engine import ProcessingEngine
from app.models.template import TemplateSection, ProcessingStrategy, TemplateInDB


def create_rate_limit_error():
    """Create a properly formatted RateLimitError."""
    response = httpx.Response(429, request=httpx.Request("POST", "https://api.openai.com"))
    return RateLimitError("Rate limit exceeded", response=response, body={"error": {"message": "Rate limit"}})


def create_api_error():
    """Create a properly formatted APIError."""
    request = httpx.Request("POST", "https://api.openai.com")
    return APIError("Internal server error", request=request, body={"error": {"message": "Internal error"}})


@pytest.fixture
def mock_db():
    """Mock MongoDB database."""
    return MagicMock()


@pytest.fixture
def processing_engine(mock_db):
    """Create processing engine with mocked dependencies."""
    with patch('app.services.processing_engine.AsyncOpenAI'):
        engine = ProcessingEngine(mock_db)
        return engine


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
def sample_section():
    """Create sample section for testing."""
    return TemplateSection(
        title="Introduction",
        guidance_prompt="Extract introduction and background",
        order=1,
        required=True
    )


@pytest.fixture
def sample_chunks():
    """Create sample relevant chunks."""
    return [
        {
            "chunk_text": "This is chunk 1 about water resources.",
            "chunk_index": 0,
            "page_number": 1,
            "section_heading": "Introduction",
            "word_count": 7,
            "similarity_score": 0.85
        },
        {
            "chunk_text": "This is chunk 2 discussing technical aspects.",
            "chunk_index": 1,
            "page_number": 2,
            "section_heading": "Technical Analysis",
            "word_count": 7,
            "similarity_score": 0.78
        }
    ]


class TestRetryConfiguration:
    """Test retry configuration constants."""

    def test_max_retries_configured(self, processing_engine):
        """Test that MAX_RETRIES is properly configured."""
        assert processing_engine.MAX_RETRIES == 3

    def test_retry_delay_base_configured(self, processing_engine):
        """Test that RETRY_DELAY_BASE is properly configured."""
        assert processing_engine.RETRY_DELAY_BASE == 2

    def test_openai_timeout_configured(self, processing_engine):
        """Test that OPENAI_TIMEOUT is properly configured."""
        assert processing_engine.OPENAI_TIMEOUT == 120


class TestOpenAIRetryLogic:
    """Test OpenAI API retry logic with exponential backoff."""

    @pytest.mark.asyncio
    async def test_successful_synthesis_on_first_attempt(
        self, processing_engine, sample_section, sample_chunks, sample_template
    ):
        """Test successful synthesis without retries."""
        # Mock successful OpenAI response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Generated section content"

        processing_engine.openai_client.chat.completions.create = AsyncMock(
            return_value=mock_response
        )

        # Execute synthesis
        result = await processing_engine._pass_3_synthesize_section(
            sample_section,
            sample_chunks,
            sample_template
        )

        # Verify result
        assert result == "Generated section content"
        assert processing_engine.openai_client.chat.completions.create.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_timeout_error(
        self, processing_engine, sample_section, sample_chunks, sample_template
    ):
        """Test retry logic on APITimeoutError."""
        # Mock OpenAI to fail twice then succeed
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Generated after retry"

        processing_engine.openai_client.chat.completions.create = AsyncMock(
            side_effect=[
                APITimeoutError("Timeout"),
                APITimeoutError("Timeout again"),
                mock_response
            ]
        )

        # Execute synthesis
        with patch('asyncio.sleep', new_callable=AsyncMock):  # Skip actual delays
            result = await processing_engine._pass_3_synthesize_section(
                sample_section,
                sample_chunks,
                sample_template
            )

        # Verify retries occurred
        assert result == "Generated after retry"
        assert processing_engine.openai_client.chat.completions.create.call_count == 3

    @pytest.mark.asyncio
    async def test_retry_on_rate_limit_error(
        self, processing_engine, sample_section, sample_chunks, sample_template
    ):
        """Test retry logic on RateLimitError."""
        # Mock OpenAI to fail once with rate limit then succeed
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Generated after rate limit"

        processing_engine.openai_client.chat.completions.create = AsyncMock(
            side_effect=[
                create_rate_limit_error(),
                mock_response
            ]
        )

        # Execute synthesis
        with patch('asyncio.sleep', new_callable=AsyncMock):
            result = await processing_engine._pass_3_synthesize_section(
                sample_section,
                sample_chunks,
                sample_template
            )

        # Verify retry occurred
        assert result == "Generated after rate limit"
        assert processing_engine.openai_client.chat.completions.create.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_on_api_error(
        self, processing_engine, sample_section, sample_chunks, sample_template
    ):
        """Test retry logic on APIError."""
        # Mock OpenAI to fail with API error then succeed
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Generated after API error"

        processing_engine.openai_client.chat.completions.create = AsyncMock(
            side_effect=[
                create_api_error(),
                mock_response
            ]
        )

        # Execute synthesis
        with patch('asyncio.sleep', new_callable=AsyncMock):
            result = await processing_engine._pass_3_synthesize_section(
                sample_section,
                sample_chunks,
                sample_template
            )

        # Verify retry occurred
        assert result == "Generated after API error"
        assert processing_engine.openai_client.chat.completions.create.call_count == 2

    @pytest.mark.asyncio
    async def test_max_retries_exceeded_timeout(
        self, processing_engine, sample_section, sample_chunks, sample_template
    ):
        """Test that max retries are enforced for timeout errors."""
        # Mock OpenAI to always timeout
        processing_engine.openai_client.chat.completions.create = AsyncMock(
            side_effect=APITimeoutError("Persistent timeout")
        )

        # Execute synthesis and expect exception
        with patch('asyncio.sleep', new_callable=AsyncMock):
            with pytest.raises(Exception) as exc_info:
                await processing_engine._pass_3_synthesize_section(
                    sample_section,
                    sample_chunks,
                    sample_template
                )

        # Verify error message and retry count
        assert "OpenAI API timeout after" in str(exc_info.value)
        assert processing_engine.openai_client.chat.completions.create.call_count == 3

    @pytest.mark.asyncio
    async def test_max_retries_exceeded_rate_limit(
        self, processing_engine, sample_section, sample_chunks, sample_template
    ):
        """Test that max retries are enforced for rate limit errors."""
        # Mock OpenAI to always hit rate limit
        processing_engine.openai_client.chat.completions.create = AsyncMock(
            side_effect=create_rate_limit_error()
        )

        # Execute synthesis and expect exception
        with patch('asyncio.sleep', new_callable=AsyncMock):
            with pytest.raises(Exception) as exc_info:
                await processing_engine._pass_3_synthesize_section(
                    sample_section,
                    sample_chunks,
                    sample_template
                )

        # Verify error message
        assert "OpenAI rate limit exceeded" in str(exc_info.value)
        assert processing_engine.openai_client.chat.completions.create.call_count == 3


class TestExponentialBackoff:
    """Test exponential backoff delays between retries."""

    @pytest.mark.asyncio
    async def test_exponential_backoff_delays(
        self, processing_engine, sample_section, sample_chunks, sample_template
    ):
        """Test that retry delays follow exponential backoff pattern."""
        # Mock OpenAI to fail twice then succeed
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Success"

        processing_engine.openai_client.chat.completions.create = AsyncMock(
            side_effect=[
                APITimeoutError("Timeout 1"),
                APITimeoutError("Timeout 2"),
                mock_response
            ]
        )

        # Track sleep calls
        sleep_calls = []

        async def mock_sleep(duration):
            sleep_calls.append(duration)

        # Execute synthesis
        with patch('asyncio.sleep', side_effect=mock_sleep):
            await processing_engine._pass_3_synthesize_section(
                sample_section,
                sample_chunks,
                sample_template
            )

        # Verify exponential backoff: 2^1=2s, 2^2=4s
        assert len(sleep_calls) == 2
        assert sleep_calls[0] == 2  # First retry: 2^1
        assert sleep_calls[1] == 4  # Second retry: 2^2

    @pytest.mark.asyncio
    async def test_rate_limit_longer_backoff(
        self, processing_engine, sample_section, sample_chunks, sample_template
    ):
        """Test that rate limit errors use longer backoff delays."""
        # Mock OpenAI to fail with rate limit then succeed
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Success"

        processing_engine.openai_client.chat.completions.create = AsyncMock(
            side_effect=[
                create_rate_limit_error(),
                mock_response
            ]
        )

        # Track sleep calls
        sleep_calls = []

        async def mock_sleep(duration):
            sleep_calls.append(duration)

        # Execute synthesis
        with patch('asyncio.sleep', side_effect=mock_sleep):
            await processing_engine._pass_3_synthesize_section(
                sample_section,
                sample_chunks,
                sample_template
            )

        # Verify longer backoff for rate limits: 2^(1+1)=4s
        assert len(sleep_calls) == 1
        assert sleep_calls[0] == 4  # Rate limit: 2^(attempt+1)


class TestTimeoutHandling:
    """Test timeout handling in OpenAI client initialization."""

    def test_openai_client_has_timeout(self, mock_db):
        """Test that OpenAI client is initialized with timeout."""
        with patch('app.services.processing_engine.AsyncOpenAI') as mock_openai:
            engine = ProcessingEngine(mock_db)

            # Verify AsyncOpenAI was called with timeout parameter
            mock_openai.assert_called_once()
            call_kwargs = mock_openai.call_args[1]
            assert 'timeout' in call_kwargs
            assert call_kwargs['timeout'] == 120


class TestEmptyChunksHandling:
    """Test handling of empty/no relevant chunks."""

    @pytest.mark.asyncio
    async def test_no_relevant_chunks(
        self, processing_engine, sample_section, sample_template
    ):
        """Test synthesis with no relevant chunks."""
        # Execute synthesis with empty chunks
        result = await processing_engine._pass_3_synthesize_section(
            sample_section,
            [],
            sample_template
        )

        # Verify fallback message
        assert "No relevant content found" in result
        assert sample_section.title in result
        # Should not call OpenAI
        assert processing_engine.openai_client.chat.completions.create.call_count == 0


class TestErrorMessages:
    """Test user-friendly error messages."""

    @pytest.mark.asyncio
    async def test_timeout_error_message(
        self, processing_engine, sample_section, sample_chunks, sample_template
    ):
        """Test user-friendly timeout error message."""
        processing_engine.openai_client.chat.completions.create = AsyncMock(
            side_effect=APITimeoutError("Timeout")
        )

        with patch('asyncio.sleep', new_callable=AsyncMock):
            with pytest.raises(Exception) as exc_info:
                await processing_engine._pass_3_synthesize_section(
                    sample_section,
                    sample_chunks,
                    sample_template
                )

        error_message = str(exc_info.value)
        assert "OpenAI API timeout after" in error_message
        assert "Please try again later" in error_message

    @pytest.mark.asyncio
    async def test_rate_limit_error_message(
        self, processing_engine, sample_section, sample_chunks, sample_template
    ):
        """Test user-friendly rate limit error message."""
        processing_engine.openai_client.chat.completions.create = AsyncMock(
            side_effect=create_rate_limit_error()
        )

        with patch('asyncio.sleep', new_callable=AsyncMock):
            with pytest.raises(Exception) as exc_info:
                await processing_engine._pass_3_synthesize_section(
                    sample_section,
                    sample_chunks,
                    sample_template
                )

        error_message = str(exc_info.value)
        assert "OpenAI rate limit exceeded" in error_message
        assert "Please wait a few minutes" in error_message
