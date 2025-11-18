"""
Batch Processing Service

Handles batch upload of multiple documents and batch processing operations.
"""
from fastapi import UploadFile, HTTPException
from typing import List, Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
import asyncio
from datetime import datetime
import logging

from app.models.batch_job import (
    BatchJob,
    BatchJobType,
    BatchJobStatus,
    BatchItemStatus,
    DocumentCollection
)
from app.services.document_service import DocumentService
from app.services.minio_service import MinIOService

logger = logging.getLogger(__name__)


class BatchProcessor:
    """Service for batch operations on documents"""

    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        document_service: DocumentService,
        minio_service: MinIOService,
        celery_app=None
    ):
        self.db = db
        self.document_service = document_service
        self.minio_service = minio_service
        self.celery_app = celery_app
        self.batch_jobs_collection = db.batch_jobs
        self.collections_collection = db.document_collections

    async def batch_upload(
        self,
        files: List[UploadFile],
        user_id: str,
        collection_name: Optional[str] = None,
        tags: Optional[List[str]] = None,
        project_name: Optional[str] = None
    ) -> BatchJob:
        """
        Upload multiple documents and optionally create a collection

        Args:
            files: List of upload files
            user_id: User ID
            collection_name: Optional name for document collection
            tags: Optional tags to apply to all documents
            project_name: Optional project name

        Returns:
            BatchJob with tracking information
        """
        # Create batch job
        batch_job = BatchJob(
            user_id=user_id,
            job_type=BatchJobType.UPLOAD,
            total_items=len(files),
            config={
                'collection_name': collection_name,
                'tags': tags or [],
                'project_name': project_name
            }
        )

        # Save batch job to database
        await self.batch_jobs_collection.insert_one(batch_job.dict())

        # Process uploads asynchronously in background
        asyncio.create_task(
            self._process_batch_upload(batch_job.id, files, user_id, tags)
        )

        return batch_job

    async def _process_batch_upload(
        self,
        batch_job_id: str,
        files: List[UploadFile],
        user_id: str,
        tags: Optional[List[str]]
    ):
        """Process batch upload in background"""
        try:
            # Update status to processing
            await self.batch_jobs_collection.update_one(
                {'id': batch_job_id},
                {'$set': {
                    'status': BatchJobStatus.PROCESSING,
                    'started_at': datetime.utcnow()
                }}
            )

            document_ids = []

            # Process each file
            for file in files:
                try:
                    # Upload document
                    document = await self.document_service.upload_document(
                        file=file,
                        user_id=user_id,
                        tags=tags
                    )

                    document_ids.append(document.id)

                    # Update batch job with success
                    await self._update_batch_item(
                        batch_job_id,
                        document.id,
                        file.filename,
                        'success'
                    )

                    logger.info(f"Batch upload: Successfully uploaded {file.filename}")

                except Exception as e:
                    # Log failure for this file
                    logger.error(f"Batch upload: Failed to upload {file.filename}: {str(e)}")
                    await self._update_batch_item(
                        batch_job_id,
                        None,
                        file.filename,
                        'failed',
                        error_message=str(e)
                    )

            # Get batch job to check config
            batch_job_dict = await self.batch_jobs_collection.find_one({'id': batch_job_id})

            # Create collection if requested
            if batch_job_dict and batch_job_dict['config'].get('collection_name') and document_ids:
                collection = DocumentCollection(
                    user_id=user_id,
                    name=batch_job_dict['config']['collection_name'],
                    document_ids=document_ids,
                    document_count=len(document_ids),
                    tags=batch_job_dict['config'].get('tags', []),
                    project_name=batch_job_dict['config'].get('project_name')
                )

                result = await self.collections_collection.insert_one(collection.dict())

                # Update batch job with collection ID
                await self.batch_jobs_collection.update_one(
                    {'id': batch_job_id},
                    {'$set': {'collection_id': collection.id}}
                )

                logger.info(f"Created collection: {collection.name} with {len(document_ids)} documents")

            # Mark batch complete
            completed_count = len(document_ids)
            failed_count = len(files) - completed_count

            final_status = BatchJobStatus.COMPLETED
            if failed_count > 0 and completed_count > 0:
                final_status = BatchJobStatus.PARTIAL
            elif failed_count == len(files):
                final_status = BatchJobStatus.FAILED

            await self.batch_jobs_collection.update_one(
                {'id': batch_job_id},
                {'$set': {
                    'status': final_status,
                    'completed_at': datetime.utcnow()
                }}
            )

            logger.info(f"Batch upload completed: {completed_count} succeeded, {failed_count} failed")

        except Exception as e:
            logger.error(f"Batch upload process failed: {str(e)}")
            await self.batch_jobs_collection.update_one(
                {'id': batch_job_id},
                {'$set': {
                    'status': BatchJobStatus.FAILED,
                    'completed_at': datetime.utcnow()
                }}
            )

    async def _update_batch_item(
        self,
        batch_job_id: str,
        document_id: Optional[str],
        filename: str,
        status: str,
        error_message: Optional[str] = None
    ):
        """Update individual item status in batch job"""
        item_status = BatchItemStatus(
            document_id=document_id or '',
            filename=filename,
            status=status,
            error_message=error_message
        )

        update_fields = {
            '$push': {'item_statuses': item_status.dict()}
        }

        if status == 'success':
            update_fields['$inc'] = {'completed_items': 1}
        elif status == 'failed':
            update_fields['$inc'] = {'failed_items': 1}

        await self.batch_jobs_collection.update_one(
            {'id': batch_job_id},
            update_fields
        )

    async def get_batch_job(self, batch_job_id: str, user_id: str) -> Optional[BatchJob]:
        """Get batch job by ID"""
        job_dict = await self.batch_jobs_collection.find_one({
            'id': batch_job_id,
            'user_id': user_id
        })

        if job_dict:
            return BatchJob(**job_dict)
        return None

    async def list_batch_jobs(
        self,
        user_id: str,
        job_type: Optional[BatchJobType] = None,
        status: Optional[BatchJobStatus] = None,
        limit: int = 50
    ) -> List[BatchJob]:
        """List batch jobs for user"""
        query = {'user_id': user_id}

        if job_type:
            query['job_type'] = job_type
        if status:
            query['status'] = status

        cursor = self.batch_jobs_collection.find(query).sort('created_at', -1).limit(limit)
        jobs = await cursor.to_list(length=limit)

        return [BatchJob(**job) for job in jobs]

    async def create_collection(
        self,
        user_id: str,
        name: str,
        document_ids: List[str],
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        project_name: Optional[str] = None
    ) -> DocumentCollection:
        """Create a document collection"""
        collection = DocumentCollection(
            user_id=user_id,
            name=name,
            description=description,
            document_ids=document_ids,
            document_count=len(document_ids),
            tags=tags or [],
            project_name=project_name
        )

        await self.collections_collection.insert_one(collection.dict())
        return collection

    async def get_collection(
        self,
        collection_id: str,
        user_id: str
    ) -> Optional[DocumentCollection]:
        """Get collection by ID"""
        coll_dict = await self.collections_collection.find_one({
            'id': collection_id,
            'user_id': user_id
        })

        if coll_dict:
            return DocumentCollection(**coll_dict)
        return None

    async def list_collections(
        self,
        user_id: str,
        limit: int = 100
    ) -> List[DocumentCollection]:
        """List all collections for user"""
        cursor = self.collections_collection.find(
            {'user_id': user_id}
        ).sort('created_at', -1).limit(limit)

        collections = await cursor.to_list(length=limit)
        return [DocumentCollection(**coll) for coll in collections]

    async def update_collection(
        self,
        collection_id: str,
        user_id: str,
        add_document_ids: Optional[List[str]] = None,
        remove_document_ids: Optional[List[str]] = None,
        name: Optional[str] = None,
        description: Optional[str] = None
    ) -> Optional[DocumentCollection]:
        """Update collection"""
        collection = await self.get_collection(collection_id, user_id)
        if not collection:
            return None

        update_dict = {'updated_at': datetime.utcnow()}

        if add_document_ids:
            # Add new document IDs (avoid duplicates)
            new_ids = list(set(collection.document_ids + add_document_ids))
            update_dict['document_ids'] = new_ids
            update_dict['document_count'] = len(new_ids)

        if remove_document_ids:
            # Remove document IDs
            new_ids = [id for id in collection.document_ids if id not in remove_document_ids]
            update_dict['document_ids'] = new_ids
            update_dict['document_count'] = len(new_ids)

        if name:
            update_dict['name'] = name
        if description is not None:
            update_dict['description'] = description

        await self.collections_collection.update_one(
            {'id': collection_id, 'user_id': user_id},
            {'$set': update_dict}
        )

        return await self.get_collection(collection_id, user_id)

    async def delete_collection(
        self,
        collection_id: str,
        user_id: str
    ) -> bool:
        """Delete collection (documents are not deleted)"""
        result = await self.collections_collection.delete_one({
            'id': collection_id,
            'user_id': user_id
        })

        return result.deleted_count > 0
