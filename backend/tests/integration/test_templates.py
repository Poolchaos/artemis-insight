"""
Tests for template API endpoints.
"""

import pytest
from fastapi import status
from bson import ObjectId

from app.models.template import TemplateCreate, TemplateSection, ProcessingStrategy


@pytest.fixture
def admin_headers(admin_user, admin_token):
    """Create authorization headers for admin user."""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def user_headers(test_user, access_token):
    """Create authorization headers for regular user."""
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def sample_template_data():
    """Sample template creation data."""
    return {
        "name": "Test Template",
        "description": "A test template for unit testing",
        "target_length": "5 pages",
        "category": "general",
        "sections": [
            {
                "title": "Introduction",
                "guidance_prompt": "Extract the introduction and background information",
                "order": 1,
                "required": True
            },
            {
                "title": "Findings",
                "guidance_prompt": "Summarize key findings and results",
                "order": 2,
                "required": True
            },
            {
                "title": "Conclusion",
                "guidance_prompt": "Extract conclusions and recommendations",
                "order": 3,
                "required": False
            }
        ],
        "processing_strategy": {
            "approach": "multi-pass",
            "chunk_size": 500,
            "overlap": 50,
            "embedding_model": "text-embedding-3-small",
            "summarization_model": "gpt-4o-mini",
            "max_tokens_per_section": 1500,
            "temperature": 0.3
        },
        "system_prompt": "You are an expert document analyst."
    }


class TestTemplateCreation:
    """Test template creation endpoint."""

    @pytest.mark.asyncio
    async def test_create_template_as_admin(
        self,
        client,
        admin_headers,
        sample_template_data
    ):
        """Admin can create a new template."""
        response = await client.post(
            "/api/templates",
            json=sample_template_data,
            headers=admin_headers
        )

        if response.status_code != status.HTTP_201_CREATED:
            print(f"Error response: {response.json()}")

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        assert data["name"] == sample_template_data["name"]
        assert data["description"] == sample_template_data["description"]
        assert data["category"] == sample_template_data["category"]
        assert len(data["sections"]) == 3
        assert data["is_active"] is True
        assert data["is_default"] is False
        assert data["version"] == 1
        assert "_id" in data

    async def test_create_template_as_user_forbidden(
        self,
        client,
        user_headers,
        sample_template_data
    ):
        """Regular users cannot create templates."""
        response = await client.post(
            "/api/templates",
            json=sample_template_data,
            headers=user_headers
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_create_template_unauthenticated(
        self,
        client,
        sample_template_data
    ):
        """Unauthenticated requests are rejected."""
        response = await client.post(
            "/api/templates",
            json=sample_template_data
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_create_duplicate_template_name(
        self,
        client,
        admin_headers,
        sample_template_data
    ):
        """Cannot create template with duplicate name."""
        # Create first template
        await client.post(
            "/api/templates",
            json=sample_template_data,
            headers=admin_headers
        )

        # Try to create duplicate
        response = await client.post(
            "/api/templates",
            json=sample_template_data,
            headers=admin_headers
        )

        assert response.status_code == status.HTTP_409_CONFLICT
        assert "already exists" in response.json()["detail"]


class TestTemplateRetrieval:
    """Test template retrieval endpoints."""

    async def test_list_templates(
        self,
        client,
        user_headers,
        admin_headers,
        sample_template_data
    ):
        """Users can list all active templates."""
        # Create test templates
        await client.post(
            "/api/templates",
            json=sample_template_data,
            headers=admin_headers
        )

        template_data_2 = sample_template_data.copy()
        template_data_2["name"] = "Test Template 2"
        await client.post(
            "/api/templates",
            json=template_data_2,
            headers=admin_headers
        )

        # List templates as regular user
        response = await client.get(
            "/api/templates",
            headers=user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2

    async def test_list_templates_pagination(
        self,
        client,
        user_headers
    ):
        """Template listing supports pagination."""
        response = await client.get(
            "/api/templates?skip=0&limit=10",
            headers=user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 10

    async def test_list_templates_by_category(
        self,
        client,
        user_headers,
        admin_headers,
        sample_template_data
    ):
        """Templates can be filtered by category."""
        # Create templates with different categories
        template_1 = sample_template_data.copy()
        template_1["name"] = "Engineering Template"
        template_1["category"] = "engineering"
        await client.post(
            "/api/templates",
            json=template_1,
            headers=admin_headers
        )

        template_2 = sample_template_data.copy()
        template_2["name"] = "General Template"
        template_2["category"] = "general"
        await client.post(
            "/api/templates",
            json=template_2,
            headers=admin_headers
        )

        # Filter by category
        response = await client.get(
            "/api/templates?category=engineering",
            headers=user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert all(t["category"] == "engineering" for t in data)

    async def test_get_template_by_id(
        self,
        client,
        user_headers,
        admin_headers,
        sample_template_data
    ):
        """Users can retrieve template by ID."""
        # Create template
        create_response = await client.post(
            "/api/templates",
            json=sample_template_data,
            headers=admin_headers
        )
        template_id = create_response.json()["_id"]

        # Get template
        response = await client.get(
            f"/api/templates/{template_id}",
            headers=user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["_id"] == template_id
        assert data["name"] == sample_template_data["name"]

    async def test_get_nonexistent_template(
        self,
        client,
        user_headers
    ):
        """Getting nonexistent template returns 404."""
        fake_id = str(ObjectId())
        response = await client.get(
            f"/api/templates/{fake_id}",
            headers=user_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_get_default_templates(
        self,
        client,
        user_headers
    ):
        """Users can retrieve default system templates."""
        response = await client.get(
            "/api/templates/defaults",
            headers=user_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        # Check if Feasibility Study template exists after seeding
        assert all(t.get("is_default") is True for t in data)


class TestTemplateUpdate:
    """Test template update endpoint."""

    async def test_update_template_as_admin(
        self,
        client,
        admin_headers,
        sample_template_data
    ):
        """Admin can update template."""
        # Create template
        create_response = await client.post(
            "/api/templates",
            json=sample_template_data,
            headers=admin_headers
        )
        template_id = create_response.json()["_id"]

        # Update template
        update_data = {
            "description": "Updated description",
            "system_prompt": "Updated system prompt"
        }
        response = await client.put(
            f"/api/templates/{template_id}",
            json=update_data,
            headers=admin_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["description"] == update_data["description"]
        assert data["system_prompt"] == update_data["system_prompt"]
        assert data["version"] == 2  # Version incremented

    async def test_update_template_as_user_forbidden(
        self,
        client,
        user_headers,
        admin_headers,
        sample_template_data
    ):
        """Regular users cannot update templates."""
        # Create template as admin
        create_response = await client.post(
            "/api/templates",
            json=sample_template_data,
            headers=admin_headers
        )
        template_id = create_response.json()["_id"]

        # Try to update as user
        update_data = {"description": "Hacked description"}
        response = await client.put(
            f"/api/templates/{template_id}",
            json=update_data,
            headers=user_headers
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_update_nonexistent_template(
        self,
        client,
        admin_headers
    ):
        """Updating nonexistent template returns 404."""
        fake_id = str(ObjectId())
        update_data = {"description": "Test"}

        response = await client.put(
            f"/api/templates/{fake_id}",
            json=update_data,
            headers=admin_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestTemplateDeletion:
    """Test template deletion endpoint."""

    async def test_delete_template_as_admin(
        self,
        client,
        admin_headers,
        sample_template_data
    ):
        """Admin can delete template."""
        # Create template
        create_response = await client.post(
            "/api/templates",
            json=sample_template_data,
            headers=admin_headers
        )
        template_id = create_response.json()["_id"]

        # Delete template
        response = await client.delete(
            f"/api/templates/{template_id}",
            headers=admin_headers
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify template no longer appears in listings
        list_response = client.get(
            "/api/templates",
            headers=admin_headers
        )
        templates = list_response.json()
        assert not any(t["_id"] == template_id for t in templates)

    async def test_delete_template_as_user_forbidden(
        self,
        client,
        user_headers,
        admin_headers,
        sample_template_data
    ):
        """Regular users cannot delete templates."""
        # Create template as admin
        create_response = await client.post(
            "/api/templates",
            json=sample_template_data,
            headers=admin_headers
        )
        template_id = create_response.json()["_id"]

        # Try to delete as user
        response = await client.delete(
            f"/api/templates/{template_id}",
            headers=user_headers
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_delete_nonexistent_template(
        self,
        client,
        admin_headers
    ):
        """Deleting nonexistent template returns 404."""
        fake_id = str(ObjectId())

        response = await client.delete(
            f"/api/templates/{fake_id}",
            headers=admin_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestTemplateSeeding:
    """Test default template seeding."""

    async def test_seed_default_templates(
        self,
        client,
        admin_headers
    ):
        """Admin can seed default templates."""
        response = await client.post(
            "/api/templates/seed",
            headers=admin_headers
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "message" in data
        assert "templates" in data
        assert "Feasibility Study Summary" in data["templates"]
        assert "Executive Summary" in data["templates"]

    async def test_seed_templates_idempotent(
        self,
        client,
        admin_headers
    ):
        """Seeding templates multiple times doesn't create duplicates."""
        # Seed once
        response1 = await client.post(
            "/api/templates/seed",
            headers=admin_headers
        )
        template_ids_1 = response1.json()["templates"]

        # Seed again
        response2 = await client.post(
            "/api/templates/seed",
            headers=admin_headers
        )
        template_ids_2 = response2.json()["templates"]

        # Should return same IDs (no duplicates created)
        assert template_ids_1 == template_ids_2

    async def test_seed_templates_as_user_forbidden(
        self,
        client,
        user_headers
    ):
        """Regular users cannot seed templates."""
        response = await client.post(
            "/api/templates/seed",
            headers=user_headers
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
