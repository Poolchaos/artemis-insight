"""
Unit tests for Celery tasks.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from bson import ObjectId

from app.tasks import generate_summary_task, regenerate_section_task
from app.models.job import JobStatus
from app.models.summary import SummaryStatus
from app.models.document import DocumentInDB, DocumentStatus
from app.models.template import TemplateInDB, TemplateSection, ProcessingStrategy


@pytest.fixture
def mock_db():
    """Mock database connection."""
    db = Mock()
    db.jobs = Mock()
    db.summaries = Mock()
    db.documents = Mock()
    db.templates = Mock()
    return db


@pytest.fixture
def sample_document():
    """Sample document for testing."""
    return DocumentInDB(
        _id=ObjectId(),
        user_id=ObjectId(),
        filename="test_feasibility_study.pdf",
        file_path="/app/uploads/test_feasibility_study.pdf",
        file_size=1024000,
        mime_type="application/pdf",
        storage_key="documents/test_feasibility_study.pdf",
        status=DocumentStatus.COMPLETED
    )


@pytest.fixture
def sample_template():
    """Sample template for testing."""
    return TemplateInDB(
        _id=ObjectId(),
        name="Feasibility Study Summary",
        description="Comprehensive feasibility study analysis",
        target_length="10 pages",
        category="engineering",
        sections=[
            TemplateSection(
                title="Introduction",
                guidance_prompt="Extract introduction and background",
                order=1,
                required=True
            ),
            TemplateSection(
                title="References",
                guidance_prompt="Extract key references",
                order=2,
                required=True
            )
        ],
        processing_strategy=ProcessingStrategy(),
        system_prompt="You are an expert technical consultant.",
        is_active=True
    )


@pytest.fixture
def processing_result():
    """Sample processing result from ProcessingEngine."""
    return {
        "document_id": "507f1f77bcf86cd799439011",
        "template_id": "507f1f77bcf86cd799439012",
        "template_name": "Feasibility Study Summary",
        "started_at": datetime.utcnow(),
        "completed_at": datetime.utcnow(),
        "status": "completed",
        "sections": [
            {
                "title": "Introduction",
                "order": 1,
                "content": "The proposed water treatment facility aims to provide...",
                "source_chunks": 15,
                "pages_referenced": [1, 2, 3, 5],
                "word_count": 285,
                "generated_at": datetime.utcnow()
            },
            {
                "title": "References",
                "order": 2,
                "content": "Key references include Namibia Water Corporation guidelines...",
                "source_chunks": 8,
                "pages_referenced": [5, 10, 15],
                "word_count": 180,
                "generated_at": datetime.utcnow()
            }
        ],
        "metadata": {
            "total_pages": 401,
            "total_words": 147618,
            "total_chunks": 300,
            "embedding_count": 300
        }
    }


class TestGenerateSummaryTask:
    """Tests for generate_summary_task."""
    
    @patch('app.tasks.get_db')
    @patch('app.tasks.DocumentService')
    @patch('app.tasks.TemplateService')
    @patch('app.tasks.ProcessingEngine')
    def test_successful_summary_generation(
        self,
        mock_engine_class,
        mock_template_service_class,
        mock_document_service_class,
        mock_get_db,
        mock_db,
        sample_document,
        sample_template,
        processing_result
    ):
        """Test successful summary generation flow."""
        # Setup mocks
        mock_get_db.return_value = mock_db
        
        # Mock services
        mock_doc_service = Mock()
        mock_doc_service.get_document.return_value = sample_document
        mock_document_service_class.return_value = mock_doc_service
        
        mock_template_service = Mock()
        mock_template_service.get_template.return_value = sample_template
        mock_template_service_class.return_value = mock_template_service
        
        # Mock ProcessingEngine
        mock_engine = Mock()
        mock_engine.process_document.return_value = processing_result
        mock_engine_class.return_value = mock_engine
        
        # Mock database operations
        mock_db.summaries.insert_one.return_value = Mock()
        mock_db.summaries.update_one.return_value = Mock()
        mock_db.jobs.update_one.return_value = Mock()
        
        # Create mock task with update_state
        mock_task = Mock()
        mock_task.update_state = Mock()
        
        # Execute task
        result = generate_summary_task.run(
            document_id=str(sample_document.id),
            template_id=str(sample_template.id),
            user_id=str(sample_document.user_id),
            job_id=str(ObjectId())
        )
        
        # Assertions
        assert result["status"] == "completed"
        assert result["document_id"] == str(sample_document.id)
        assert result["template_name"] == "Feasibility Study Summary"
        assert result["section_count"] == 2
        assert result["total_word_count"] == 465  # 285 + 180
        
        # Verify service calls
        mock_doc_service.get_document.assert_called_once()
        mock_template_service.get_template.assert_called_once()
        mock_engine.process_document.assert_called_once()
        
        # Verify database operations
        assert mock_db.summaries.insert_one.called
        assert mock_db.summaries.update_one.called
        assert mock_db.jobs.update_one.call_count >= 2  # Initial RUNNING + final COMPLETED
    
    @patch('app.tasks.get_db')
    @patch('app.tasks.DocumentService')
    def test_document_not_found(
        self,
        mock_document_service_class,
        mock_get_db,
        mock_db
    ):
        """Test error handling when document is not found."""
        mock_get_db.return_value = mock_db
        
        mock_doc_service = Mock()
        mock_doc_service.get_document.return_value = None
        mock_document_service_class.return_value = mock_doc_service
        
        mock_db.jobs.update_one.return_value = Mock()
        mock_db.summaries.update_one.return_value = Mock()
        
        mock_task = Mock()
        
        with pytest.raises(ValueError, match="Document not found"):
            generate_summary_task.run(
                document_id=str(ObjectId()),
                template_id=str(ObjectId()),
                user_id=str(ObjectId()),
                job_id=str(ObjectId())
            )
        
        # Verify error was recorded in job
        job_update_calls = [call for call in mock_db.jobs.update_one.call_args_list if "error_message" in str(call)]
        assert len(job_update_calls) > 0
    
    @patch('app.tasks.get_db')
    @patch('app.tasks.DocumentService')
    @patch('app.tasks.TemplateService')
    def test_template_not_found(
        self,
        mock_template_service_class,
        mock_document_service_class,
        mock_get_db,
        mock_db,
        sample_document
    ):
        """Test error handling when template is not found."""
        mock_get_db.return_value = mock_db
        
        mock_doc_service = Mock()
        mock_doc_service.get_document.return_value = sample_document
        mock_document_service_class.return_value = mock_doc_service
        
        mock_template_service = Mock()
        mock_template_service.get_template.return_value = None
        mock_template_service_class.return_value = mock_template_service
        
        mock_db.jobs.update_one.return_value = Mock()
        mock_db.summaries.update_one.return_value = Mock()
        
        mock_task = Mock()
        
        with pytest.raises(ValueError, match="Template not found"):
            generate_summary_task.run(
                document_id=str(sample_document.id),
                template_id=str(ObjectId()),
                user_id=str(sample_document.user_id),
                job_id=str(ObjectId())
            )
    
    @patch('app.tasks.get_db')
    @patch('app.tasks.DocumentService')
    @patch('app.tasks.TemplateService')
    @patch('app.tasks.ProcessingEngine')
    def test_processing_engine_failure(
        self,
        mock_engine_class,
        mock_template_service_class,
        mock_document_service_class,
        mock_get_db,
        mock_db,
        sample_document,
        sample_template
    ):
        """Test error handling when ProcessingEngine fails."""
        mock_get_db.return_value = mock_db
        
        # Mock services
        mock_doc_service = Mock()
        mock_doc_service.get_document.return_value = sample_document
        mock_document_service_class.return_value = mock_doc_service
        
        mock_template_service = Mock()
        mock_template_service.get_template.return_value = sample_template
        mock_template_service_class.return_value = mock_template_service
        
        # Mock ProcessingEngine to raise exception
        mock_engine = Mock()
        mock_engine.process_document.side_effect = Exception("OpenAI API rate limit exceeded")
        mock_engine_class.return_value = mock_engine
        
        # Mock database operations
        mock_db.summaries.insert_one.return_value = Mock()
        mock_db.jobs.update_one.return_value = Mock()
        mock_db.summaries.update_one.return_value = Mock()
        
        mock_task = Mock()
        
        with pytest.raises(Exception, match="OpenAI API rate limit exceeded"):
            generate_summary_task.run(
                document_id=str(sample_document.id),
                template_id=str(sample_template.id),
                user_id=str(sample_document.user_id),
                job_id=str(ObjectId())
            )
        
        # Verify error was recorded in both job and summary
        job_update_calls = [call for call in mock_db.jobs.update_one.call_args_list if "error_message" in str(call)]
        assert len(job_update_calls) > 0
        
        summary_update_calls = [call for call in mock_db.summaries.update_one.call_args_list if "error_message" in str(call)]
        assert len(summary_update_calls) > 0
    
    @patch('app.tasks.get_db')
    @patch('app.tasks.DocumentService')
    @patch('app.tasks.TemplateService')
    @patch('app.tasks.ProcessingEngine')
    def test_progress_callbacks(
        self,
        mock_engine_class,
        mock_template_service_class,
        mock_document_service_class,
        mock_get_db,
        mock_db,
        sample_document,
        sample_template,
        processing_result
    ):
        """Test that progress callbacks update job and task state."""
        mock_get_db.return_value = mock_db
        
        # Mock services
        mock_doc_service = Mock()
        mock_doc_service.get_document.return_value = sample_document
        mock_document_service_class.return_value = mock_doc_service
        
        mock_template_service = Mock()
        mock_template_service.get_template.return_value = sample_template
        mock_template_service_class.return_value = mock_template_service
        
        # Mock ProcessingEngine and capture progress callback
        progress_callback = None
        def capture_callback(*args, **kwargs):
            nonlocal progress_callback
            progress_callback = kwargs.get('progress_callback')
            return processing_result
        
        mock_engine = Mock()
        mock_engine.process_document = Mock(side_effect=capture_callback)
        mock_engine_class.return_value = mock_engine
        
        # Mock database operations
        mock_db.summaries.insert_one.return_value = Mock()
        mock_db.summaries.update_one.return_value = Mock()
        mock_db.jobs.update_one.return_value = Mock()
        
        mock_task = Mock()
        mock_task.update_state = Mock()
        
        # Execute task
        generate_summary_task.run(
            document_id=str(sample_document.id),
            template_id=str(sample_template.id),
            user_id=str(sample_document.user_id),
            job_id=str(ObjectId())
        )
        
        # Test progress callback
        assert progress_callback is not None
        progress_callback(50, "Processing sections")
        
        # Verify progress updates
        assert mock_db.jobs.update_one.called
        assert mock_task.update_state.called
        
        # Find the call with progress=50
        progress_calls = [call for call in mock_task.update_state.call_args_list 
                         if call[1].get('meta', {}).get('progress') == 50]
        assert len(progress_calls) > 0


class TestRegenerateSectionTask:
    """Tests for regenerate_section_task."""
    
    @patch('app.tasks.get_db')
    @patch('app.tasks.DocumentService')
    @patch('app.tasks.TemplateService')
    @patch('app.tasks.ProcessingEngine')
    def test_successful_section_regeneration(
        self,
        mock_engine_class,
        mock_template_service_class,
        mock_document_service_class,
        mock_get_db,
        mock_db,
        sample_document,
        sample_template
    ):
        """Test successful section regeneration."""
        summary_id = ObjectId()
        user_id = ObjectId()
        
        mock_get_db.return_value = mock_db
        
        # Mock existing summary
        mock_db.summaries.find_one.return_value = {
            "_id": summary_id,
            "document_id": sample_document.id,
            "user_id": user_id,
            "template_id": str(sample_template.id),
            "sections": [
                {
                    "title": "Introduction",
                    "order": 1,
                    "content": "Old content...",
                    "source_chunks": 10,
                    "pages_referenced": [1, 2],
                    "word_count": 150,
                    "generated_at": datetime.utcnow()
                }
            ]
        }
        
        # Mock services
        mock_doc_service = Mock()
        mock_doc_service.get_document.return_value = sample_document
        mock_document_service_class.return_value = mock_doc_service
        
        mock_template_service = Mock()
        mock_template_service.get_template.return_value = sample_template
        mock_template_service_class.return_value = mock_template_service
        
        # Mock ProcessingEngine
        new_section = {
            "title": "Introduction",
            "order": 1,
            "content": "Updated introduction with improved analysis...",
            "source_chunks": 15,
            "pages_referenced": [1, 2, 3, 5],
            "word_count": 285,
            "generated_at": datetime.utcnow()
        }
        mock_engine = Mock()
        mock_engine.regenerate_section.return_value = new_section
        mock_engine_class.return_value = mock_engine
        
        # Mock database operations
        mock_db.summaries.update_one.return_value = Mock()
        mock_db.jobs.update_one.return_value = Mock()
        
        mock_task = Mock()
        mock_task.update_state = Mock()
        
        # Execute task
        result = regenerate_section_task.run(
            summary_id=str(summary_id),
            section_title="Introduction",
            user_id=str(user_id),
            job_id=str(ObjectId())
        )
        
        # Assertions
        assert result["status"] == "completed"
        assert result["summary_id"] == str(summary_id)
        assert result["section_title"] == "Introduction"
        assert result["word_count"] == 285
        assert result["source_chunks"] == 15
        
        # Verify service calls
        mock_engine.regenerate_section.assert_called_once()
        assert mock_db.summaries.update_one.called
        assert mock_db.jobs.update_one.call_count >= 2
    
    @patch('app.tasks.get_db')
    def test_summary_not_found(
        self,
        mock_get_db,
        mock_db
    ):
        """Test error handling when summary is not found."""
        mock_get_db.return_value = mock_db
        mock_db.summaries.find_one.return_value = None
        mock_db.jobs.update_one.return_value = Mock()
        
        mock_task = Mock()
        
        with pytest.raises(ValueError, match="Summary not found"):
            regenerate_section_task.run(
                summary_id=str(ObjectId()),
                section_title="Introduction",
                user_id=str(ObjectId()),
                job_id=str(ObjectId())
            )
    
    @patch('app.tasks.get_db')
    @patch('app.tasks.DocumentService')
    @patch('app.tasks.TemplateService')
    @patch('app.tasks.ProcessingEngine')
    def test_regeneration_failure(
        self,
        mock_engine_class,
        mock_template_service_class,
        mock_document_service_class,
        mock_get_db,
        mock_db,
        sample_document,
        sample_template
    ):
        """Test error handling when regeneration fails."""
        summary_id = ObjectId()
        user_id = ObjectId()
        
        mock_get_db.return_value = mock_db
        
        # Mock existing summary
        mock_db.summaries.find_one.return_value = {
            "_id": summary_id,
            "document_id": sample_document.id,
            "user_id": user_id,
            "template_id": str(sample_template.id)
        }
        
        # Mock services
        mock_doc_service = Mock()
        mock_doc_service.get_document.return_value = sample_document
        mock_document_service_class.return_value = mock_doc_service
        
        mock_template_service = Mock()
        mock_template_service.get_template.return_value = sample_template
        mock_template_service_class.return_value = mock_template_service
        
        # Mock ProcessingEngine to raise exception
        mock_engine = Mock()
        mock_engine.regenerate_section.side_effect = Exception("Section not found in template")
        mock_engine_class.return_value = mock_engine
        
        mock_db.jobs.update_one.return_value = Mock()
        
        mock_task = Mock()
        
        with pytest.raises(Exception, match="Section not found in template"):
            regenerate_section_task.run(
                summary_id=str(summary_id),
                section_title="NonExistentSection",
                user_id=str(user_id),
                job_id=str(ObjectId())
            )
        
        # Verify error was recorded in job
        job_update_calls = [call for call in mock_db.jobs.update_one.call_args_list if "error_message" in str(call)]
        assert len(job_update_calls) > 0
