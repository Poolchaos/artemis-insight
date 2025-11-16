"""
Celery tasks for asynchronous document processing.
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any
from bson import ObjectId

from app.celery_app import celery_app
from app.database import get_db
from app.services.processing_engine import ProcessingEngine
from app.services.template_service import TemplateService
from app.services.document_service import DocumentService
from app.models.job import JobStatus
from app.models.summary import (
    SummaryStatus,
    SummarySection,
    ProcessingMetadata,
    SummaryInDB,
)

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.tasks.generate_summary")
def generate_summary_task(
    self,
    document_id: str,
    template_id: str,
    user_id: str,
    job_id: str
) -> Dict[str, Any]:
    """
    Generate AI summary for a document using specified template.

    This task orchestrates the multi-pass AI processing pipeline:
    1. Retrieves document and template from database
    2. Initializes ProcessingEngine
    3. Executes 4-pass processing with progress updates
    4. Stores results in Summary collection
    5. Updates Job status and links summary_id

    Args:
        document_id: Document to process
        template_id: Template defining summary structure
        user_id: User who initiated the job
        job_id: Job tracking ID

    Returns:
        Dictionary with summary_id and processing metadata

    Raises:
        Exception: If processing fails at any stage
    """
    db = get_db()

    try:
        # Update job status to RUNNING
        db.jobs.update_one(
            {"_id": ObjectId(job_id)},
            {
                "$set": {
                    "status": JobStatus.RUNNING,
                    "progress": 0,
                    "updated_at": datetime.utcnow()
                }
            }
        )

        logger.info(f"Starting summary generation: document={document_id}, template={template_id}, job={job_id}")

        # Retrieve document
        document_service = DocumentService(db)
        document = document_service.get_document(document_id, user_id)
        if not document:
            raise ValueError(f"Document not found: {document_id}")

        # Retrieve template
        template_service = TemplateService(db)
        template = template_service.get_template(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")

        logger.info(f"Retrieved document: {document.filename} ({document.file_size} bytes)")
        logger.info(f"Using template: {template.name} with {len(template.sections)} sections")

        # Create Summary record in PROCESSING state
        summary_id = ObjectId()
        summary_doc = SummaryInDB(
            _id=summary_id,
            document_id=ObjectId(document_id),
            user_id=ObjectId(user_id),
            template_id=template_id,
            template_name=template.name,
            job_id=ObjectId(job_id),
            status=SummaryStatus.PROCESSING,
            sections=[],
            metadata=None,
            started_at=datetime.utcnow()
        )

        db.summaries.insert_one(summary_doc.model_dump(by_alias=True))
        logger.info(f"Created summary record: {summary_id}")

        # Define progress callback to update job progress
        def update_progress(progress: int, message: str = ""):
            """Update job progress and log message."""
            db.jobs.update_one(
                {"_id": ObjectId(job_id)},
                {
                    "$set": {
                        "progress": progress,
                        "updated_at": datetime.utcnow()
                    }
                }
            )

            # Update Celery task state for monitoring
            self.update_state(
                state="PROGRESS",
                meta={
                    "progress": progress,
                    "message": message,
                    "document_id": document_id,
                    "template_name": template.name
                }
            )

            logger.info(f"Progress: {progress}% - {message}")

        # Initialize ProcessingEngine
        engine = ProcessingEngine(db)

        # Execute multi-pass processing
        update_progress(5, "Starting document processing")

        processing_result = engine.process_document(
            document_id=document_id,
            file_path=document.file_path,
            template=template,
            progress_callback=update_progress
        )

        logger.info(f"Processing completed: {len(processing_result['sections'])} sections generated")

        # Convert processing result sections to SummarySection models
        summary_sections = [
            SummarySection(
                title=section["title"],
                order=section["order"],
                content=section["content"],
                source_chunks=section["source_chunks"],
                pages_referenced=section["pages_referenced"],
                word_count=section["word_count"],
                generated_at=section["generated_at"]
            )
            for section in processing_result["sections"]
        ]

        # Create ProcessingMetadata
        processing_metadata = ProcessingMetadata(
            total_pages=processing_result["metadata"]["total_pages"],
            total_words=processing_result["metadata"]["total_words"],
            total_chunks=processing_result["metadata"]["total_chunks"],
            embedding_count=processing_result["metadata"]["embedding_count"],
            processing_duration_seconds=(
                processing_result["completed_at"] - processing_result["started_at"]
            ).total_seconds()
        )

        # Update summary with results
        db.summaries.update_one(
            {"_id": summary_id},
            {
                "$set": {
                    "status": SummaryStatus.COMPLETED,
                    "sections": [s.model_dump() for s in summary_sections],
                    "metadata": processing_metadata.model_dump(),
                    "completed_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
            }
        )

        logger.info(f"Summary updated successfully: {summary_id}")

        # Update job status to COMPLETED with summary_id link
        update_progress(100, "Summary generation completed")
        db.jobs.update_one(
            {"_id": ObjectId(job_id)},
            {
                "$set": {
                    "status": JobStatus.COMPLETED,
                    "progress": 100,
                    "summary_id": summary_id,
                    "completed_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
            }
        )

        logger.info(f"Job completed successfully: {job_id}")

        return {
            "summary_id": str(summary_id),
            "document_id": document_id,
            "template_name": template.name,
            "section_count": len(summary_sections),
            "total_word_count": sum(s.word_count for s in summary_sections),
            "processing_duration": processing_metadata.processing_duration_seconds,
            "status": "completed"
        }

    except Exception as e:
        logger.error(f"Summary generation failed: {str(e)}", exc_info=True)

        # Update job status to FAILED
        db.jobs.update_one(
            {"_id": ObjectId(job_id)},
            {
                "$set": {
                    "status": JobStatus.FAILED,
                    "error_message": str(e),
                    "completed_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
            }
        )

        # Update summary status to FAILED if it exists
        db.summaries.update_one(
            {"job_id": ObjectId(job_id)},
            {
                "$set": {
                    "status": SummaryStatus.FAILED,
                    "error_message": str(e),
                    "completed_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
            }
        )

        # Re-raise exception for Celery to handle
        raise


@celery_app.task(bind=True, name="app.tasks.regenerate_section")
def regenerate_section_task(
    self,
    summary_id: str,
    section_title: str,
    user_id: str,
    job_id: str
) -> Dict[str, Any]:
    """
    Regenerate a single section within an existing summary.

    Useful for iterative refinement when a section needs improvement.

    Args:
        summary_id: Summary to update
        section_title: Title of section to regenerate
        user_id: User who initiated the job
        job_id: Job tracking ID

    Returns:
        Dictionary with updated section metadata

    Raises:
        Exception: If regeneration fails
    """
    db = get_db()

    try:
        # Update job status to RUNNING
        db.jobs.update_one(
            {"_id": ObjectId(job_id)},
            {
                "$set": {
                    "status": JobStatus.RUNNING,
                    "progress": 0,
                    "updated_at": datetime.utcnow()
                }
            }
        )

        logger.info(f"Regenerating section: summary={summary_id}, section={section_title}, job={job_id}")

        # Retrieve summary
        summary = db.summaries.find_one({"_id": ObjectId(summary_id), "user_id": ObjectId(user_id)})
        if not summary:
            raise ValueError(f"Summary not found: {summary_id}")

        # Retrieve document and template
        document_id = str(summary["document_id"])
        template_id = summary["template_id"]

        document_service = DocumentService(db)
        document = document_service.get_document(document_id, user_id)
        if not document:
            raise ValueError(f"Document not found: {document_id}")

        template_service = TemplateService(db)
        template = template_service.get_template(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")

        # Initialize ProcessingEngine
        engine = ProcessingEngine(db)

        # Regenerate section
        self.update_state(state="PROGRESS", meta={"progress": 50, "message": f"Regenerating {section_title}"})

        new_section = engine.regenerate_section(
            document_id=document_id,
            file_path=document.file_path,
            template=template,
            section_title=section_title
        )

        # Convert to SummarySection
        updated_section = SummarySection(
            title=new_section["title"],
            order=new_section["order"],
            content=new_section["content"],
            source_chunks=new_section["source_chunks"],
            pages_referenced=new_section["pages_referenced"],
            word_count=new_section["word_count"],
            generated_at=new_section["generated_at"]
        )

        # Update section in summary
        db.summaries.update_one(
            {"_id": ObjectId(summary_id), "sections.title": section_title},
            {
                "$set": {
                    "sections.$": updated_section.model_dump(),
                    "updated_at": datetime.utcnow()
                }
            }
        )

        # Update job status to COMPLETED
        db.jobs.update_one(
            {"_id": ObjectId(job_id)},
            {
                "$set": {
                    "status": JobStatus.COMPLETED,
                    "progress": 100,
                    "completed_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
            }
        )

        logger.info(f"Section regenerated successfully: {section_title}")

        return {
            "summary_id": summary_id,
            "section_title": section_title,
            "word_count": updated_section.word_count,
            "source_chunks": updated_section.source_chunks,
            "status": "completed"
        }

    except Exception as e:
        logger.error(f"Section regeneration failed: {str(e)}", exc_info=True)

        # Update job status to FAILED
        db.jobs.update_one(
            {"_id": ObjectId(job_id)},
            {
                "$set": {
                    "status": JobStatus.FAILED,
                    "error_message": str(e),
                    "completed_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
            }
        )

        raise
