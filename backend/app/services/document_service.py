"""
Document service for managing PDF documents and metadata.
"""

import logging
from typing import List, Optional
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.models.document import (
    DocumentCreate,
    DocumentUpdate,
    DocumentInDB,
    DocumentStatus
)
from app.models.user import PyObjectId
from app.services.minio_service import minio_service

logger = logging.getLogger(__name__)


class DocumentService:
    """Service for document CRUD operations."""

    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize document service.

        Args:
            db: MongoDB database instance
        """
        self.db = db
        self.collection = db.documents

    async def create_document(
        self,
        document_data: DocumentCreate,
        file_path: str
    ) -> DocumentInDB:
        """
        Create a new document record.

        Args:
            document_data: Document creation data
            file_path: Path to file in MinIO

        Returns:
            Created document with ID
        """
        document_dict = document_data.model_dump()
        document_dict['user_id'] = ObjectId(document_data.user_id)
        document_dict['file_path'] = file_path
        document_dict['created_at'] = datetime.utcnow()
        document_dict['updated_at'] = datetime.utcnow()
        document_dict['upload_date'] = datetime.utcnow()

        result = await self.collection.insert_one(document_dict)
        document_dict['_id'] = result.inserted_id

        return DocumentInDB(**document_dict)

    async def get_document(self, document_id: str) -> Optional[DocumentInDB]:
        """
        Get a document by ID.

        Args:
            document_id: Document ID

        Returns:
            Document if found, None otherwise
        """
        try:
            doc_id = ObjectId(document_id)
        except Exception:
            return None

        document = await self.collection.find_one({'_id': doc_id})
        if document:
            return DocumentInDB(**document)
        return None

    async def get_document_by_user(
        self,
        document_id: str,
        user_id: str
    ) -> Optional[DocumentInDB]:
        """
        Get a document by ID, ensuring it belongs to the user.

        Args:
            document_id: Document ID
            user_id: User ID

        Returns:
            Document if found and belongs to user, None otherwise
        """
        try:
            doc_id = ObjectId(document_id)
            uid = ObjectId(user_id)
        except Exception:
            return None

        document = await self.collection.find_one({
            '_id': doc_id,
            'user_id': uid
        })
        if document:
            return DocumentInDB(**document)
        return None

    async def list_user_documents(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 100,
        status: Optional[DocumentStatus] = None
    ) -> List[DocumentInDB]:
        """
        List documents for a user.

        Args:
            user_id: User ID
            skip: Number of documents to skip
            limit: Maximum number of documents to return
            status: Optional status filter

        Returns:
            List of documents
        """
        try:
            uid = ObjectId(user_id)
        except Exception:
            return []

        query = {'user_id': uid}
        if status:
            query['status'] = status

        cursor = self.collection.find(query).skip(skip).limit(limit).sort('created_at', -1)
        documents = await cursor.to_list(length=limit)

        return [DocumentInDB(**doc) for doc in documents]

    async def update_document(
        self,
        document_id: str,
        update_data: DocumentUpdate
    ) -> Optional[DocumentInDB]:
        """
        Update a document.

        Args:
            document_id: Document ID
            update_data: Fields to update

        Returns:
            Updated document if found, None otherwise
        """
        try:
            doc_id = ObjectId(document_id)
        except Exception:
            return None

        update_dict = update_data.model_dump(exclude_unset=True)
        if not update_dict:
            return await self.get_document(document_id)

        update_dict['updated_at'] = datetime.utcnow()

        result = await self.collection.find_one_and_update(
            {'_id': doc_id},
            {'$set': update_dict},
            return_document=True
        )

        if result:
            return DocumentInDB(**result)
        return None

    def update_document_status(
        self,
        document_id: str,
        status: 'DocumentStatus'
    ) -> bool:
        """
        Update document status (synchronous for Celery tasks).

        Args:
            document_id: Document ID
            status: New status

        Returns:
            True if updated, False otherwise
        """
        try:
            from pymongo import MongoClient
            from app.config import settings

            # Create sync MongoDB client for Celery task
            client = MongoClient(settings.MONGODB_URL)
            db = client[settings.DATABASE_NAME]
            collection = db['documents']

            doc_id = ObjectId(document_id)
            result = collection.update_one(
                {'_id': doc_id},
                {
                    '$set': {
                        'status': status.value,
                        'updated_at': datetime.utcnow()
                    }
                }
            )

            client.close()
            return result.modified_count > 0

        except Exception as e:
            logger.error(f"Failed to update document status: {str(e)}")
            return False

    async def delete_document(self, document_id: str, user_id: str) -> bool:
        """
        Delete a document and its file from storage.

        Args:
            document_id: Document ID
            user_id: User ID (for authorization)

        Returns:
            True if deleted, False otherwise
        """
        document = await self.get_document_by_user(document_id, user_id)
        if not document:
            return False

        # Delete file from MinIO
        try:
            minio_service.delete_file(document.file_path)
        except Exception:
            # Log error but continue with database deletion
            pass

        # Delete from database
        result = await self.collection.delete_one({'_id': ObjectId(document_id)})
        return result.deleted_count > 0

    async def count_user_documents(
        self,
        user_id: str,
        status: Optional[DocumentStatus] = None
    ) -> int:
        """
        Count documents for a user.

        Args:
            user_id: User ID
            status: Optional status filter

        Returns:
            Number of documents
        """
        try:
            uid = ObjectId(user_id)
        except Exception:
            return 0

        query = {'user_id': uid}
        if status:
            query['status'] = status

        return await self.collection.count_documents(query)
