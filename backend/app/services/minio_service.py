"""
MinIO storage service for managing file operations.
"""

import io
from typing import Optional, BinaryIO
from datetime import timedelta
import boto3
from botocore.exceptions import ClientError
from botocore.config import Config

from app.config import settings


class MinIOService:
    """Service for interacting with MinIO object storage."""

    def __init__(self):
        """Initialize MinIO client."""
        # Ensure endpoint has http:// or https:// prefix
        endpoint = settings.minio_endpoint
        if not endpoint.startswith(('http://', 'https://')):
            endpoint = f"http://{endpoint}"

        self.client = boto3.client(
            's3',
            endpoint_url=endpoint,
            aws_access_key_id=settings.minio_access_key,
            aws_secret_access_key=settings.minio_secret_key,
            config=Config(signature_version='s3v4'),
            region_name='us-east-1'
        )
        self.bucket_name = settings.minio_bucket
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self) -> None:
        """Create bucket if it doesn't exist."""
        try:
            self.client.head_bucket(Bucket=self.bucket_name)
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code')
            if error_code == '404':
                # Bucket doesn't exist, create it
                self.client.create_bucket(Bucket=self.bucket_name)
            else:
                raise

    def upload_file(
        self,
        file: BinaryIO,
        object_name: str,
        content_type: str = "application/pdf"
    ) -> str:
        """
        Upload a file to MinIO.

        Args:
            file: File-like object to upload
            object_name: Name/path for the object in MinIO
            content_type: MIME type of the file

        Returns:
            The object name/path in MinIO

        Raises:
            ClientError: If upload fails
        """
        try:
            self.client.upload_fileobj(
                file,
                self.bucket_name,
                object_name,
                ExtraArgs={'ContentType': content_type}
            )
            return object_name
        except ClientError as e:
            raise Exception(f"Failed to upload file to MinIO: {str(e)}")

    def download_file(self, object_name: str) -> bytes:
        """
        Download a file from MinIO.

        Args:
            object_name: Name/path of the object in MinIO

        Returns:
            File content as bytes

        Raises:
            ClientError: If download fails
        """
        try:
            buffer = io.BytesIO()
            self.client.download_fileobj(self.bucket_name, object_name, buffer)
            buffer.seek(0)
            return buffer.read()
        except ClientError as e:
            if e.response.get('Error', {}).get('Code') == 'NoSuchKey':
                raise FileNotFoundError(f"File not found: {object_name}")
            raise Exception(f"Failed to download file from MinIO: {str(e)}")

    def delete_file(self, object_name: str) -> bool:
        """
        Delete a file from MinIO.

        Args:
            object_name: Name/path of the object in MinIO

        Returns:
            True if deletion was successful

        Raises:
            ClientError: If deletion fails
        """
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=object_name)
            return True
        except ClientError as e:
            raise Exception(f"Failed to delete file from MinIO: {str(e)}")

    def get_presigned_url(
        self,
        object_name: str,
        expiration: int = 3600
    ) -> str:
        """
        Generate a presigned URL for temporary file access.

        Args:
            object_name: Name/path of the object in MinIO
            expiration: URL expiration time in seconds (default: 1 hour)

        Returns:
            Presigned URL string

        Raises:
            ClientError: If URL generation fails
        """
        try:
            url = self.client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': object_name},
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            raise Exception(f"Failed to generate presigned URL: {str(e)}")

    def file_exists(self, object_name: str) -> bool:
        """
        Check if a file exists in MinIO.

        Args:
            object_name: Name/path of the object in MinIO

        Returns:
            True if file exists, False otherwise
        """
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=object_name)
            return True
        except ClientError as e:
            if e.response.get('Error', {}).get('Code') == '404':
                return False
            raise

    def get_file_size(self, object_name: str) -> int:
        """
        Get the size of a file in MinIO.

        Args:
            object_name: Name/path of the object in MinIO

        Returns:
            File size in bytes

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        try:
            response = self.client.head_object(Bucket=self.bucket_name, Key=object_name)
            return response['ContentLength']
        except ClientError as e:
            if e.response.get('Error', {}).get('Code') == '404':
                raise FileNotFoundError(f"File not found: {object_name}")
            raise Exception(f"Failed to get file size: {str(e)}")


# Singleton instance
minio_service = MinIOService()
