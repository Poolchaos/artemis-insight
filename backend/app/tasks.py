"""
Celery tasks for asynchronous document processing.
"""

import logging
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

from app.celery_app import celery_app
from app.database import get_db
from app.services.processing_engine import ProcessingEngine
from app.services.template_service import TemplateService
from app.services.document_service import DocumentService
from app.models.job import JobStatus
from app.models.document import DocumentStatus
from app.models.summary import (
    SummaryStatus,
    SummarySection,
    ProcessingMetadata,
    SummaryInDB,
)

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.tasks.process_document")
def process_document_task(
    self,
    document_id: str,
    user_id: str
) -> Dict[str, Any]:
    """
    Process an uploaded document (OCR, text extraction, etc.).

    This task:
    1. Updates document status to PROCESSING
    2. Performs OCR/text extraction (placeholder for now)
    3. Updates document status to COMPLETED

    Args:
        document_id: Document to process
        user_id: User who owns the document

    Returns:
        Dict with processing results
    """
    logger.info(f"Starting document processing: document_id={document_id}")

    try:
        from pymongo import MongoClient
        from app.config import settings
        from PyPDF2 import PdfReader
        import io

        # Create sync MongoDB client for Celery task
        client = MongoClient(settings.mongo_uri)
        db = client.get_default_database()
        collection = db['documents']

        from bson import ObjectId
        doc_id = ObjectId(document_id)

        # Get document from database
        doc = collection.find_one({'_id': doc_id})
        if not doc:
            raise ValueError(f"Document {document_id} not found")

        # Update status to PROCESSING
        collection.update_one(
            {'_id': doc_id},
            {
                '$set': {
                    'status': DocumentStatus.PROCESSING.value,
                    'updated_at': datetime.utcnow()
                }
            }
        )
        logger.info(f"Document {document_id} status updated to PROCESSING")

        # Download PDF from MinIO and extract page count
        try:
            from app.services.minio_service import MinioService
            minio_service = MinioService()
            file_data = minio_service.download_file(doc['file_path'])

            # Extract page count using PyPDF2
            pdf_reader = PdfReader(io.BytesIO(file_data))
            page_count = len(pdf_reader.pages)
            logger.info(f"Extracted {page_count} pages from document {document_id}")
        except Exception as e:
            logger.error(f"Failed to extract page count: {str(e)}")
            page_count = None

        # TODO: Implement actual OCR/text extraction
        # For now, we'll just mark it as completed after a short delay
        import time
        time.sleep(2)  # Simulate processing time

        # Update status to COMPLETED with page count
        update_data = {
            'status': DocumentStatus.COMPLETED.value,
            'updated_at': datetime.utcnow()
        }
        if page_count is not None:
            update_data['page_count'] = page_count

        collection.update_one(
            {'_id': doc_id},
            {'$set': update_data}
        )
        logger.info(f"Document {document_id} processing completed successfully")

        client.close()

        return {
            "status": "success",
            "document_id": document_id,
            "page_count": page_count,
            "message": "Document processed successfully"
        }

    except Exception as e:
        logger.error(f"Document processing failed: {str(e)}", exc_info=True)
        # Update status to FAILED
        try:
            from pymongo import MongoClient
            from app.config import settings
            from bson import ObjectId

            client = MongoClient(settings.mongo_uri)
            db = client.get_default_database()
            collection = db['documents']

            collection.update_one(
                {'_id': ObjectId(document_id)},
                {
                    '$set': {
                        'status': DocumentStatus.FAILED.value,
                        'updated_at': datetime.utcnow()
                    }
                }
            )
            client.close()
        except Exception:
            pass

        return {
            "status": "error",
            "document_id": document_id,
            "error": str(e)
        }


@celery_app.task(
    bind=True,
    name="app.tasks.generate_summary",
    autoretry_for=(Exception,),  # Auto-retry on any exception
    retry_kwargs={'max_retries': 2, 'countdown': 60},  # Retry up to 2 times with 60s delay
    retry_backoff=True,  # Exponential backoff
    retry_jitter=True,  # Add randomness to backoff to prevent thundering herd
    time_limit=3600,  # 1 hour hard limit
    soft_time_limit=3300  # 55 minutes soft limit
)
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
    from pymongo import MongoClient
    from app.config import settings

    # Create sync MongoDB client for Celery task
    client = MongoClient(settings.mongo_uri)
    db = client.get_default_database()

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

        # Retrieve document directly from database (sync)
        doc_dict = db.documents.find_one({
            '_id': ObjectId(document_id),
            'user_id': ObjectId(user_id)
        })
        if not doc_dict:
            raise ValueError(f"Document not found: {document_id}")

        from app.models.document import DocumentInDB
        document = DocumentInDB(**doc_dict)

        # Retrieve template directly from database (sync)
        template_dict = db.templates.find_one({'_id': ObjectId(template_id)})
        if not template_dict:
            raise ValueError(f"Template not found: {template_id}")

        from app.models.template import TemplateInDB
        template = TemplateInDB(**template_dict)

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

        # Download PDF from MinIO to temporary file
        update_progress(5, "Downloading document from storage")
        from app.services.minio_service import minio_service
        import tempfile
        import os

        file_data = minio_service.download_file(document.file_path)

        # Create temporary file with original filename extension
        temp_fd, temp_path = tempfile.mkstemp(suffix='.pdf', prefix='summary_')
        try:
            # Write PDF data to temporary file
            with os.fdopen(temp_fd, 'wb') as temp_file:
                temp_file.write(file_data)

            logger.info(f"Downloaded PDF to temporary file: {temp_path}")

            # Initialize async ProcessingEngine with async Motor client
            from app.config import settings
            async_client = AsyncIOMotorClient(settings.mongo_uri)
            async_db = async_client.get_default_database()
            engine = ProcessingEngine(async_db)

            # Execute multi-pass processing (async operation wrapped in sync context)
            update_progress(10, "Starting document processing")

            # Define async wrapper to run the processing
            async def run_processing():
                return await engine.process_document(
                    document_id=document_id,
                    file_path=temp_path,  # Use temporary local file path
                    template=template,
                    progress_callback=None  # TODO: Convert update_progress to async if needed
                )

            # Run async processing in the current thread's event loop
            processing_result = asyncio.run(run_processing())

        finally:
            # Clean up temporary file
            try:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    logger.info(f"Cleaned up temporary file: {temp_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up temporary file {temp_path}: {e}")

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

        # Create user-friendly error message
        error_message = str(e)
        user_friendly_message = error_message

        # Check for common error patterns and provide better messages
        if "401" in error_message and "api key" in error_message.lower():
            user_friendly_message = "Invalid OpenAI API key. Please check your OPENAI_API_KEY environment variable and ensure it's a valid API key from https://platform.openai.com/account/api-keys"
        elif "429" in error_message or "rate limit" in error_message.lower():
            user_friendly_message = "OpenAI API rate limit exceeded. Please try again later or check your API quota at https://platform.openai.com/account/usage"
        elif "500" in error_message or "503" in error_message:
            user_friendly_message = "OpenAI API is temporarily unavailable. Please try again in a few minutes."
        elif "timeout" in error_message.lower():
            user_friendly_message = "Request timed out while processing the document. The document may be too large or the service is slow. Please try again."
        elif "no such file" in error_message.lower() or "filenotfounderror" in error_message.lower():
            user_friendly_message = "Document file not found in storage. Please re-upload the document and try again."
        elif "permission" in error_message.lower() or "access denied" in error_message.lower():
            user_friendly_message = "Storage access error. Please contact support if this persists."

        # Update job status to FAILED
        db.jobs.update_one(
            {"_id": ObjectId(job_id)},
            {
                "$set": {
                    "status": JobStatus.FAILED,
                    "error_message": user_friendly_message,
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
                    "error_message": user_friendly_message,
                    "completed_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
            }
        )

        # Re-raise exception for Celery to handle
        raise

    finally:
        # Always close the MongoDB client
        client.close()


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
    from pymongo import MongoClient
    from app.config import settings

    # Create sync MongoDB client for Celery task
    client = MongoClient(settings.mongo_uri)
    db = client.get_default_database()

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

        # Retrieve document directly from database (sync)
        doc_dict = db.documents.find_one({
            '_id': ObjectId(document_id),
            'user_id': ObjectId(user_id)
        })
        if not doc_dict:
            raise ValueError(f"Document not found: {document_id}")

        from app.models.document import DocumentInDB
        document = DocumentInDB(**doc_dict)

        # Retrieve template directly from database (sync)
        template_dict = db.templates.find_one({'_id': ObjectId(template_id)})
        if not template_dict:
            raise ValueError(f"Template not found: {template_id}")

        from app.models.template import TemplateInDB
        template = TemplateInDB(**template_dict)

        # Download PDF from MinIO to temporary file
        from app.services.minio_service import minio_service
        import tempfile
        import os

        file_data = minio_service.download_file(document.file_path)

        # Create temporary file with original filename extension
        temp_fd, temp_path = tempfile.mkstemp(suffix='.pdf', prefix='regen_section_')
        try:
            # Write PDF data to temporary file
            with os.fdopen(temp_fd, 'wb') as temp_file:
                temp_file.write(file_data)

            logger.info(f"Downloaded PDF to temporary file: {temp_path}")

            # Initialize async ProcessingEngine with async Motor client
            from app.config import settings
            async_client = AsyncIOMotorClient(settings.mongo_uri)
            async_db = async_client.get_default_database()
            engine = ProcessingEngine(async_db)

            # Regenerate section (async operation wrapped in sync context)
            self.update_state(state="PROGRESS", meta={"progress": 50, "message": f"Regenerating {section_title}"})

            # Define async wrapper to run the regeneration
            async def run_regeneration():
                return await engine.regenerate_section(
                    document_id=document_id,
                    file_path=temp_path,  # Use temporary local file path
                    template=template,
                    section_title=section_title
                )

            # Run async regeneration in the current thread's event loop
            new_section = asyncio.run(run_regeneration())

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

        finally:
            # Clean up temporary file
            try:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    logger.info(f"Cleaned up temporary file: {temp_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up temporary file {temp_path}: {e}")

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

        # Create user-friendly error message
        error_message = str(e)
        user_friendly_message = error_message

        # Check for common error patterns and provide better messages
        if "401" in error_message and "api key" in error_message.lower():
            user_friendly_message = "Invalid OpenAI API key. Please check your OPENAI_API_KEY environment variable and ensure it's a valid API key from https://platform.openai.com/account/api-keys"
        elif "429" in error_message or "rate limit" in error_message.lower():
            user_friendly_message = "OpenAI API rate limit exceeded. Please try again later or check your API quota at https://platform.openai.com/account/usage"
        elif "500" in error_message or "503" in error_message:
            user_friendly_message = "OpenAI API is temporarily unavailable. Please try again in a few minutes."
        elif "timeout" in error_message.lower():
            user_friendly_message = "Request timed out while processing. Please try again."
        elif "no such file" in error_message.lower() or "filenotfounderror" in error_message.lower():
            user_friendly_message = "Document file not found in storage. The original document may have been deleted."

        # Update job status to FAILED
        db.jobs.update_one(
            {"_id": ObjectId(job_id)},
            {
                "$set": {
                    "status": JobStatus.FAILED,
                    "error_message": user_friendly_message,
                    "completed_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
            }
        )

        raise

    finally:
        # Always close the MongoDB client
        client.close()


@celery_app.task(bind=True, name="app.tasks.cleanup_stuck_jobs_task")
def cleanup_stuck_jobs_task(self) -> Dict[str, Any]:
    """
    Periodic task to detect and auto-fail stuck jobs.

    Runs every 5 minutes to check for jobs stuck in PENDING or RUNNING
    state for more than 60 minutes without progress.

    Returns:
        Dict with cleanup results
    """
    logger.info("Starting stuck job cleanup task")

    try:
        # Get async loop
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    async def _cleanup():
        from app.config import settings
        from app.utils.task_monitor import auto_fail_stuck_jobs

        # Create MongoDB client
        client = AsyncIOMotorClient(settings.mongo_uri)
        db = client.get_default_database()

        try:
            # Auto-fail jobs stuck for more than 60 minutes
            failed_count = await auto_fail_stuck_jobs(db, timeout_minutes=60)

            if failed_count > 0:
                logger.warning(f"Auto-failed {failed_count} stuck job(s)")
            else:
                logger.debug("No stuck jobs found")

            return {
                "status": "success",
                "failed_count": failed_count,
                "timestamp": datetime.utcnow().isoformat()
            }
        finally:
            client.close()

    # Run the async cleanup
    result = loop.run_until_complete(_cleanup())

    logger.info(f"Stuck job cleanup completed: {result}")
    return result
