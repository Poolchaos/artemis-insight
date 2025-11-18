"""
Integration tests for batch processing API
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, Mock
import io

from app.main import app


@pytest.fixture
def auth_headers(test_user_token):
    """Get authentication headers"""
    return {"Authorization": f"Bearer {test_user_token}"}


def test_batch_upload_success(client: TestClient, auth_headers):
    """Test successful batch upload"""
    # Create mock PDF files
    files = [
        ("files", ("doc1.pdf", io.BytesIO(b"PDF content 1"), "application/pdf")),
        ("files", ("doc2.pdf", io.BytesIO(b"PDF content 2"), "application/pdf")),
        ("files", ("doc3.pdf", io.BytesIO(b"PDF content 3"), "application/pdf"))
    ]

    data = {
        "collection_name": "Test Project",
        "tags": "engineering,civil",
        "project_name": "Bridge Construction"
    }

    response = client.post(
        "/api/batch/upload",
        files=files,
        data=data,
        headers=auth_headers
    )

    assert response.status_code == 200
    result = response.json()

    assert "id" in result
    assert result["job_type"] == "upload"
    assert result["status"] == "pending"
    assert result["total_items"] == 3
    assert result["completed_items"] == 0
    assert result["failed_items"] == 0


def test_batch_upload_without_collection(client: TestClient, auth_headers):
    """Test batch upload without creating collection"""
    files = [
        ("files", ("doc1.pdf", io.BytesIO(b"PDF content 1"), "application/pdf")),
        ("files", ("doc2.pdf", io.BytesIO(b"PDF content 2"), "application/pdf"))
    ]

    response = client.post(
        "/api/batch/upload",
        files=files,
        headers=auth_headers
    )

    assert response.status_code == 200
    result = response.json()
    assert result["total_items"] == 2


def test_batch_upload_no_files(client: TestClient, auth_headers):
    """Test batch upload with no files"""
    response = client.post(
        "/api/batch/upload",
        files=[],
        headers=auth_headers
    )

    assert response.status_code == 400
    assert "No files provided" in response.json()["detail"]


def test_batch_upload_too_many_files(client: TestClient, auth_headers):
    """Test batch upload with too many files (>50)"""
    files = [
        ("files", (f"doc{i}.pdf", io.BytesIO(b"PDF content"), "application/pdf"))
        for i in range(51)
    ]

    response = client.post(
        "/api/batch/upload",
        files=files,
        headers=auth_headers
    )

    assert response.status_code == 400
    assert "Maximum 50 files" in response.json()["detail"]


def test_batch_upload_invalid_file_type(client: TestClient, auth_headers):
    """Test batch upload with non-PDF file"""
    files = [
        ("files", ("doc1.pdf", io.BytesIO(b"PDF content"), "application/pdf")),
        ("files", ("doc2.docx", io.BytesIO(b"Word content"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document"))
    ]

    response = client.post(
        "/api/batch/upload",
        files=files,
        headers=auth_headers
    )

    assert response.status_code == 400
    assert "Only PDF files are supported" in response.json()["detail"]


def test_batch_upload_unauthorized(client: TestClient):
    """Test batch upload without authentication"""
    files = [
        ("files", ("doc1.pdf", io.BytesIO(b"PDF content"), "application/pdf"))
    ]

    response = client.post("/api/batch/upload", files=files)

    assert response.status_code == 401


def test_get_batch_job_status(client: TestClient, auth_headers, sample_batch_job):
    """Test getting batch job status"""
    job_id = sample_batch_job["id"]

    response = client.get(
        f"/api/batch/jobs/{job_id}",
        headers=auth_headers
    )

    assert response.status_code == 200
    result = response.json()

    assert result["id"] == job_id
    assert "status" in result
    assert "total_items" in result
    assert "completed_items" in result


def test_get_batch_job_not_found(client: TestClient, auth_headers):
    """Test getting non-existent batch job"""
    response = client.get(
        "/api/batch/jobs/nonexistent",
        headers=auth_headers
    )

    assert response.status_code == 404


def test_list_batch_jobs(client: TestClient, auth_headers):
    """Test listing batch jobs"""
    response = client.get(
        "/api/batch/jobs",
        headers=auth_headers
    )

    assert response.status_code == 200
    result = response.json()
    assert isinstance(result, list)


def test_list_batch_jobs_with_filters(client: TestClient, auth_headers):
    """Test listing batch jobs with filters"""
    response = client.get(
        "/api/batch/jobs?job_type=upload&status=completed&limit=10",
        headers=auth_headers
    )

    assert response.status_code == 200
    result = response.json()
    assert isinstance(result, list)


def test_create_collection(client: TestClient, auth_headers):
    """Test creating a document collection"""
    payload = {
        "name": "Engineering Specs",
        "document_ids": ["doc1", "doc2", "doc3"],
        "description": "Engineering specifications for project",
        "tags": ["engineering", "specs"],
        "project_name": "Bridge Project"
    }

    response = client.post(
        "/api/batch/collections",
        json=payload,
        headers=auth_headers
    )

    assert response.status_code == 200
    result = response.json()

    assert result["name"] == "Engineering Specs"
    assert result["document_count"] == 3
    assert len(result["document_ids"]) == 3
    assert result["project_name"] == "Bridge Project"


def test_create_collection_invalid_data(client: TestClient, auth_headers):
    """Test creating collection with invalid data"""
    payload = {
        "name": "",  # Empty name
        "document_ids": []  # No documents
    }

    response = client.post(
        "/api/batch/collections",
        json=payload,
        headers=auth_headers
    )

    assert response.status_code == 422  # Validation error


def test_get_collection(client: TestClient, auth_headers, sample_collection):
    """Test getting a collection by ID"""
    collection_id = sample_collection["id"]

    response = client.get(
        f"/api/batch/collections/{collection_id}",
        headers=auth_headers
    )

    assert response.status_code == 200
    result = response.json()

    assert result["id"] == collection_id
    assert result["name"] == sample_collection["name"]


def test_get_collection_not_found(client: TestClient, auth_headers):
    """Test getting non-existent collection"""
    response = client.get(
        "/api/batch/collections/nonexistent",
        headers=auth_headers
    )

    assert response.status_code == 404


def test_list_collections(client: TestClient, auth_headers):
    """Test listing all collections"""
    response = client.get(
        "/api/batch/collections",
        headers=auth_headers
    )

    assert response.status_code == 200
    result = response.json()
    assert isinstance(result, list)


def test_update_collection_add_documents(client: TestClient, auth_headers, sample_collection):
    """Test adding documents to a collection"""
    collection_id = sample_collection["id"]

    payload = {
        "add_document_ids": ["doc4", "doc5"]
    }

    response = client.patch(
        f"/api/batch/collections/{collection_id}",
        json=payload,
        headers=auth_headers
    )

    assert response.status_code == 200
    result = response.json()

    assert "doc4" in result["document_ids"]
    assert "doc5" in result["document_ids"]


def test_update_collection_remove_documents(client: TestClient, auth_headers, sample_collection):
    """Test removing documents from a collection"""
    collection_id = sample_collection["id"]

    payload = {
        "remove_document_ids": ["doc1"]
    }

    response = client.patch(
        f"/api/batch/collections/{collection_id}",
        json=payload,
        headers=auth_headers
    )

    assert response.status_code == 200
    result = response.json()

    assert "doc1" not in result["document_ids"]


def test_update_collection_rename(client: TestClient, auth_headers, sample_collection):
    """Test renaming a collection"""
    collection_id = sample_collection["id"]

    payload = {
        "name": "Updated Collection Name",
        "description": "Updated description"
    }

    response = client.patch(
        f"/api/batch/collections/{collection_id}",
        json=payload,
        headers=auth_headers
    )

    assert response.status_code == 200
    result = response.json()

    assert result["name"] == "Updated Collection Name"
    assert result["description"] == "Updated description"


def test_delete_collection(client: TestClient, auth_headers, sample_collection):
    """Test deleting a collection"""
    collection_id = sample_collection["id"]

    response = client.delete(
        f"/api/batch/collections/{collection_id}",
        headers=auth_headers
    )

    assert response.status_code == 204


def test_delete_collection_not_found(client: TestClient, auth_headers):
    """Test deleting non-existent collection"""
    response = client.delete(
        "/api/batch/collections/nonexistent",
        headers=auth_headers
    )

    assert response.status_code == 404
