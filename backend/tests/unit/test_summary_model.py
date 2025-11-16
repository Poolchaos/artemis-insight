"""
Unit tests for Summary models.
"""

from datetime import datetime
import pytest
from bson import ObjectId

from app.models.summary import (
    SummaryStatus,
    SummarySection,
    ProcessingMetadata,
    SummaryCreate,
    SummaryUpdate,
    SummaryInDB,
    SummaryResponse,
    SummaryListItem,
)


class TestSummarySection:
    """Tests for SummarySection model."""

    def test_create_summary_section(self):
        """Test creating a valid summary section."""
        section = SummarySection(
            title="Introduction",
            order=1,
            content="The proposed water treatment facility aims to provide...",
            source_chunks=15,
            pages_referenced=[1, 2, 3, 5, 8],
            word_count=285,
            generated_at=datetime.utcnow()
        )

        assert section.title == "Introduction"
        assert section.order == 1
        assert section.source_chunks == 15
        assert len(section.pages_referenced) == 5
        assert section.word_count == 285

    def test_summary_section_default_pages(self):
        """Test summary section with default empty pages list."""
        section = SummarySection(
            title="Conclusion",
            order=9,
            content="Final recommendations...",
            source_chunks=10,
            word_count=150,
            generated_at=datetime.utcnow()
        )

        assert section.pages_referenced == []


class TestProcessingMetadata:
    """Tests for ProcessingMetadata model."""

    def test_create_processing_metadata(self):
        """Test creating processing metadata."""
        metadata = ProcessingMetadata(
            total_pages=401,
            total_words=147618,
            total_chunks=300,
            embedding_count=300,
            processing_duration_seconds=285.5,
            estimated_cost_usd=1.85
        )

        assert metadata.total_pages == 401
        assert metadata.total_words == 147618
        assert metadata.total_chunks == 300
        assert metadata.embedding_count == 300
        assert metadata.processing_duration_seconds == 285.5
        assert metadata.estimated_cost_usd == 1.85

    def test_metadata_optional_fields(self):
        """Test metadata with optional fields omitted."""
        metadata = ProcessingMetadata(
            total_pages=100,
            total_words=50000,
            total_chunks=100,
            embedding_count=100
        )

        assert metadata.processing_duration_seconds is None
        assert metadata.estimated_cost_usd is None


class TestSummaryCreate:
    """Tests for SummaryCreate model."""

    def test_create_summary_valid_ids(self):
        """Test creating summary with valid ObjectIds."""
        document_id = str(ObjectId())
        user_id = str(ObjectId())
        template_id = str(ObjectId())

        summary_create = SummaryCreate(
            document_id=document_id,
            user_id=user_id,
            template_id=template_id,
            template_name="Feasibility Study Summary"
        )

        assert summary_create.document_id == document_id
        assert summary_create.user_id == user_id
        assert summary_create.template_id == template_id
        assert summary_create.template_name == "Feasibility Study Summary"

    def test_create_summary_invalid_document_id(self):
        """Test creating summary with invalid document_id."""
        with pytest.raises(ValueError, match="Invalid ObjectId"):
            SummaryCreate(
                document_id="invalid_id",
                user_id=str(ObjectId()),
                template_id=str(ObjectId()),
                template_name="Test Template"
            )

    def test_create_summary_with_job_id(self):
        """Test creating summary with optional job_id."""
        summary_create = SummaryCreate(
            document_id=str(ObjectId()),
            user_id=str(ObjectId()),
            template_id=str(ObjectId()),
            template_name="Test Template",
            job_id=str(ObjectId())
        )

        assert summary_create.job_id is not None


class TestSummaryUpdate:
    """Tests for SummaryUpdate model."""

    def test_update_status(self):
        """Test updating summary status."""
        update = SummaryUpdate(status=SummaryStatus.COMPLETED)
        assert update.status == SummaryStatus.COMPLETED
        assert update.sections is None

    def test_update_with_sections(self):
        """Test updating summary with sections."""
        section = SummarySection(
            title="Introduction",
            order=1,
            content="Content...",
            source_chunks=10,
            word_count=100,
            generated_at=datetime.utcnow()
        )

        update = SummaryUpdate(
            status=SummaryStatus.COMPLETED,
            sections=[section]
        )

        assert update.status == SummaryStatus.COMPLETED
        assert len(update.sections) == 1
        assert update.sections[0].title == "Introduction"

    def test_update_with_error(self):
        """Test updating summary with error message."""
        update = SummaryUpdate(
            status=SummaryStatus.FAILED,
            error_message="OpenAI API rate limit exceeded"
        )

        assert update.status == SummaryStatus.FAILED
        assert update.error_message == "OpenAI API rate limit exceeded"


class TestSummaryInDB:
    """Tests for SummaryInDB model."""

    def test_create_summary_in_db(self):
        """Test creating SummaryInDB with all fields."""
        document_id = ObjectId()
        user_id = ObjectId()
        template_id = str(ObjectId())

        section = SummarySection(
            title="Introduction",
            order=1,
            content="The proposed facility...",
            source_chunks=15,
            pages_referenced=[1, 2, 3],
            word_count=250,
            generated_at=datetime.utcnow()
        )

        metadata = ProcessingMetadata(
            total_pages=401,
            total_words=147618,
            total_chunks=300,
            embedding_count=300
        )

        summary = SummaryInDB(
            document_id=document_id,
            user_id=user_id,
            template_id=template_id,
            template_name="Feasibility Study Summary",
            status=SummaryStatus.COMPLETED,
            sections=[section],
            metadata=metadata
        )

        assert summary.document_id == document_id
        assert summary.user_id == user_id
        assert summary.template_id == template_id
        assert summary.status == SummaryStatus.COMPLETED
        assert len(summary.sections) == 1
        assert summary.metadata.total_pages == 401
        assert summary.created_at is not None
        assert summary.updated_at is not None

    def test_summary_in_db_default_values(self):
        """Test SummaryInDB with default values."""
        summary = SummaryInDB(
            document_id=ObjectId(),
            user_id=ObjectId(),
            template_id=str(ObjectId()),
            template_name="Test Template"
        )

        assert summary.status == SummaryStatus.PROCESSING
        assert summary.sections == []
        assert summary.metadata is None
        assert summary.error_message is None
        assert summary.completed_at is None
        assert summary.job_id is None


class TestSummaryResponse:
    """Tests for SummaryResponse model."""

    def test_summary_response_conversion(self):
        """Test converting SummaryInDB to SummaryResponse."""
        document_id = ObjectId()
        user_id = ObjectId()
        summary_id = ObjectId()

        section = SummarySection(
            title="References",
            order=1,
            content="Key references include...",
            source_chunks=8,
            pages_referenced=[5, 10, 15],
            word_count=180,
            generated_at=datetime.utcnow()
        )

        summary_in_db = SummaryInDB(
            _id=summary_id,
            document_id=document_id,
            user_id=user_id,
            template_id=str(ObjectId()),
            template_name="Executive Summary",
            status=SummaryStatus.COMPLETED,
            sections=[section]
        )

        # Convert to response model
        response = SummaryResponse(
            id=str(summary_in_db.id),
            document_id=str(summary_in_db.document_id),
            user_id=str(summary_in_db.user_id),
            template_id=summary_in_db.template_id,
            template_name=summary_in_db.template_name,
            status=summary_in_db.status,
            sections=summary_in_db.sections,
            metadata=summary_in_db.metadata,
            error_message=summary_in_db.error_message,
            started_at=summary_in_db.started_at,
            completed_at=summary_in_db.completed_at,
            created_at=summary_in_db.created_at,
            updated_at=summary_in_db.updated_at,
            job_id=str(summary_in_db.job_id) if summary_in_db.job_id else None
        )

        assert response.id == str(summary_id)
        assert response.document_id == str(document_id)
        assert response.user_id == str(user_id)
        assert response.template_name == "Executive Summary"
        assert response.status == SummaryStatus.COMPLETED
        assert len(response.sections) == 1


class TestSummaryListItem:
    """Tests for SummaryListItem model."""

    def test_summary_list_item(self):
        """Test creating summary list item."""
        list_item = SummaryListItem(
            id=str(ObjectId()),
            document_id=str(ObjectId()),
            template_name="Feasibility Study Summary",
            status=SummaryStatus.COMPLETED,
            section_count=9,
            total_word_count=2500,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow()
        )

        assert list_item.template_name == "Feasibility Study Summary"
        assert list_item.status == SummaryStatus.COMPLETED
        assert list_item.section_count == 9
        assert list_item.total_word_count == 2500
        assert list_item.completed_at is not None

    def test_summary_list_item_in_progress(self):
        """Test list item for in-progress summary."""
        list_item = SummaryListItem(
            id=str(ObjectId()),
            document_id=str(ObjectId()),
            template_name="Executive Summary",
            status=SummaryStatus.PROCESSING,
            section_count=0,
            total_word_count=0,
            started_at=datetime.utcnow()
        )

        assert list_item.status == SummaryStatus.PROCESSING
        assert list_item.section_count == 0
        assert list_item.total_word_count == 0
        assert list_item.completed_at is None
