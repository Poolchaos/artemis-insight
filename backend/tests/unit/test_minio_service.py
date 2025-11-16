"""
Unit tests for MinIO service.
"""

import pytest
from io import BytesIO
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError

from app.services.minio_service import MinIOService, minio_service


@pytest.fixture
def mock_s3_client():
    """Create a mock S3 client."""
    client = Mock()
    return client


@pytest.fixture
def minio_service_instance(mock_s3_client):
    """Create MinIO service instance with mocked S3 client."""
    with patch('app.services.minio_service.boto3.client') as mock_boto:
        mock_boto.return_value = mock_s3_client
        service = MinIOService()
        service.s3_client = mock_s3_client
        yield service


class TestMinIOService:
    """Test MinIO service functionality."""

    def test_singleton_instance(self):
        """Test that minio_service is a singleton instance."""
        assert isinstance(minio_service, MinIOService)

    def test_upload_file_success(self, minio_service_instance, mock_s3_client):
        """Test successful file upload."""
        # Arrange
        file_content = b"test content"
        file_obj = BytesIO(file_content)
        object_name = "test/file.txt"
        content_type = "text/plain"

        # Act
        minio_service_instance.upload_file(file_obj, object_name, content_type)

        # Assert
        mock_s3_client.upload_fileobj.assert_called_once()
        call_args = mock_s3_client.upload_fileobj.call_args
        assert call_args[0][1] == minio_service_instance.bucket_name
        assert call_args[0][2] == object_name
        assert call_args[1]['ExtraArgs']['ContentType'] == content_type

    def test_upload_file_error(self, minio_service_instance, mock_s3_client):
        """Test file upload with ClientError."""
        # Arrange
        file_obj = BytesIO(b"test")
        object_name = "test/file.txt"
        error_response = {'Error': {'Code': '500', 'Message': 'Internal Error'}}
        mock_s3_client.upload_fileobj.side_effect = ClientError(error_response, 'upload_fileobj')

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            minio_service_instance.upload_file(file_obj, object_name, "text/plain")
        assert "Failed to upload" in str(exc_info.value)

    def test_download_file_success(self, minio_service_instance, mock_s3_client):
        """Test successful file download."""
        # Arrange
        object_name = "test/file.txt"
        expected_content = b"test content"

        def mock_download(bucket, key, fileobj):
            fileobj.write(expected_content)

        mock_s3_client.download_fileobj.side_effect = mock_download

        # Act
        result = minio_service_instance.download_file(object_name)

        # Assert
        assert result == expected_content
        mock_s3_client.download_fileobj.assert_called_once()

    def test_download_file_not_found(self, minio_service_instance, mock_s3_client):
        """Test downloading non-existent file."""
        # Arrange
        object_name = "test/missing.txt"
        error_response = {'Error': {'Code': 'NoSuchKey', 'Message': 'Not found'}}
        mock_s3_client.download_fileobj.side_effect = ClientError(error_response, 'download_fileobj')

        # Act & Assert
        with pytest.raises(FileNotFoundError) as exc_info:
            minio_service_instance.download_file(object_name)
        assert "File not found" in str(exc_info.value)

    def test_delete_file_success(self, minio_service_instance, mock_s3_client):
        """Test successful file deletion."""
        # Arrange
        object_name = "test/file.txt"

        # Act
        minio_service_instance.delete_file(object_name)

        # Assert
        mock_s3_client.delete_object.assert_called_once_with(
            Bucket=minio_service_instance.bucket_name,
            Key=object_name
        )

    def test_delete_file_error(self, minio_service_instance, mock_s3_client):
        """Test file deletion with error."""
        # Arrange
        object_name = "test/file.txt"
        error_response = {'Error': {'Code': '500', 'Message': 'Internal Error'}}
        mock_s3_client.delete_object.side_effect = ClientError(error_response, 'delete_object')

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            minio_service_instance.delete_file(object_name)
        assert "Failed to delete" in str(exc_info.value)

    def test_get_presigned_url_success(self, minio_service_instance, mock_s3_client):
        """Test generating presigned URL."""
        # Arrange
        object_name = "test/file.txt"
        expected_url = "https://minio.example.com/bucket/test/file.txt?signature=xyz"
        mock_s3_client.generate_presigned_url.return_value = expected_url

        # Act
        result = minio_service_instance.get_presigned_url(object_name, expiration=3600)

        # Assert
        assert result == expected_url
        mock_s3_client.generate_presigned_url.assert_called_once_with(
            'get_object',
            Params={
                'Bucket': minio_service_instance.bucket_name,
                'Key': object_name
            },
            ExpiresIn=3600
        )

    def test_get_presigned_url_error(self, minio_service_instance, mock_s3_client):
        """Test presigned URL generation with error."""
        # Arrange
        object_name = "test/file.txt"
        error_response = {'Error': {'Code': '500', 'Message': 'Internal Error'}}
        mock_s3_client.generate_presigned_url.side_effect = ClientError(error_response, 'generate_presigned_url')

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            minio_service_instance.get_presigned_url(object_name)
        assert "Failed to generate presigned URL" in str(exc_info.value)

    def test_file_exists_true(self, minio_service_instance, mock_s3_client):
        """Test checking file existence when file exists."""
        # Arrange
        object_name = "test/file.txt"
        mock_s3_client.head_object.return_value = {'ContentLength': 100}

        # Act
        result = minio_service_instance.file_exists(object_name)

        # Assert
        assert result is True
        mock_s3_client.head_object.assert_called_once_with(
            Bucket=minio_service_instance.bucket_name,
            Key=object_name
        )

    def test_file_exists_false(self, minio_service_instance, mock_s3_client):
        """Test checking file existence when file doesn't exist."""
        # Arrange
        object_name = "test/missing.txt"
        error_response = {'Error': {'Code': '404', 'Message': 'Not Found'}}
        mock_s3_client.head_object.side_effect = ClientError(error_response, 'head_object')

        # Act
        result = minio_service_instance.file_exists(object_name)

        # Assert
        assert result is False

    def test_file_exists_error(self, minio_service_instance, mock_s3_client):
        """Test file existence check with unexpected error."""
        # Arrange
        object_name = "test/file.txt"
        error_response = {'Error': {'Code': '500', 'Message': 'Internal Error'}}
        mock_s3_client.head_object.side_effect = ClientError(error_response, 'head_object')

        # Act & Assert - Should raise exception for non-404 errors
        with pytest.raises(ClientError):
            minio_service_instance.file_exists(object_name)

    def test_get_file_size_success(self, minio_service_instance, mock_s3_client):
        """Test getting file size."""
        # Arrange
        object_name = "test/file.txt"
        expected_size = 12345
        mock_s3_client.head_object.return_value = {'ContentLength': expected_size}

        # Act
        result = minio_service_instance.get_file_size(object_name)

        # Assert
        assert result == expected_size
        mock_s3_client.head_object.assert_called_once_with(
            Bucket=minio_service_instance.bucket_name,
            Key=object_name
        )

    def test_get_file_size_not_found(self, minio_service_instance, mock_s3_client):
        """Test getting size of non-existent file."""
        # Arrange
        object_name = "test/missing.txt"
        error_response = {'Error': {'Code': '404', 'Message': 'Not Found'}}
        mock_s3_client.head_object.side_effect = ClientError(error_response, 'head_object')

        # Act & Assert
        with pytest.raises(FileNotFoundError) as exc_info:
            minio_service_instance.get_file_size(object_name)
        assert "File not found" in str(exc_info.value)

    def test_get_file_size_error(self, minio_service_instance, mock_s3_client):
        """Test getting file size with error."""
        # Arrange
        object_name = "test/file.txt"
        error_response = {'Error': {'Code': '500', 'Message': 'Internal Error'}}
        mock_s3_client.head_object.side_effect = ClientError(error_response, 'head_object')

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            minio_service_instance.get_file_size(object_name)
        assert "Failed to get file size" in str(exc_info.value)

    @patch('app.services.minio_service.boto3.client')
    def test_ensure_bucket_exists_creates_bucket(self, mock_boto_client):
        """Test bucket creation when it doesn't exist."""
        # Arrange
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        error_response = {'Error': {'Code': '404', 'Message': 'Not Found'}}
        mock_client.head_bucket.side_effect = ClientError(error_response, 'head_bucket')

        # Act
        service = MinIOService()

        # Assert
        mock_client.create_bucket.assert_called_once()

    @patch('app.services.minio_service.boto3.client')
    def test_ensure_bucket_exists_bucket_already_exists(self, mock_boto_client):
        """Test when bucket already exists."""
        # Arrange
        mock_client = Mock()
        mock_boto_client.return_value = mock_client
        mock_client.head_bucket.return_value = {}  # Success means bucket exists

        # Act
        service = MinIOService()

        # Assert
        mock_client.create_bucket.assert_not_called()
