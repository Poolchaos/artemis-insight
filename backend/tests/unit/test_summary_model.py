"""
Unit tests for summary and template models.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError
from bson import ObjectId

from app.models.summary import (
    SummaryBase,
    SummaryCreate,
    SummaryInDB,
    SummaryResponse,
    TemplateField,
    TemplateBase,
    TemplateCreate,
    TemplateUpdate,
    TemplateInDB,
    TemplateResponse
)


# Summary Model Tests

def test_summary_base_valid():
    """Test valid summary base creation."""
    summary = SummaryBase(
        summary_text="This is a summary",
        model_used="gpt-4",
        confidence_scores={"overall": 0.95}
    )
    assert summary.summary_text == "This is a summary"
    assert summary.model_used == "gpt-4"
    assert summary.confidence_scores["overall"] == 0.95


def test_summary_base_invalid_confidence_score():
    """Test summary with invalid confidence score."""
    with pytest.raises(ValidationError) as exc_info:
        SummaryBase(
            summary_text="Summary",
            model_used="gpt-4",
            confidence_scores={"score": 1.5}
        )
    assert "must be between 0 and 1" in str(exc_info.value)


def test_summary_base_negative_confidence():
    """Test summary with negative confidence score."""
    with pytest.raises(ValidationError) as exc_info:
        SummaryBase(
            summary_text="Summary",
            model_used="gpt-4",
            confidence_scores={"score": -0.1}
        )
    assert "must be between 0 and 1" in str(exc_info.value)


def test_summary_create_valid():
    """Test valid summary creation."""
    summary = SummaryCreate(
        document_id=str(ObjectId()),
        user_id=str(ObjectId()),
        summary_text="Document summary",
        model_used="gpt-4",
        extraction_data={"key": "value"}
    )
    assert summary.summary_text == "Document summary"
    assert summary.extraction_data["key"] == "value"


def test_summary_create_invalid_document_id():
    """Test summary create with invalid document ID."""
    with pytest.raises(ValidationError) as exc_info:
        SummaryCreate(
            document_id="invalid-id",
            user_id=str(ObjectId()),
            summary_text="Summary",
            model_used="gpt-4"
        )
    assert "Invalid ObjectId" in str(exc_info.value)


def test_summary_in_db():
    """Test summary in database schema."""
    summary = SummaryInDB(
        document_id=ObjectId(),
        user_id=ObjectId(),
        summary_text="Summary text",
        model_used="gpt-4"
    )
    assert summary.id is not None
    assert isinstance(summary.created_at, datetime)
    assert isinstance(summary.updated_at, datetime)


def test_summary_response():
    """Test summary API response schema."""
    response = SummaryResponse(
        id=str(ObjectId()),
        document_id=str(ObjectId()),
        user_id=str(ObjectId()),
        summary_text="Summary",
        model_used="gpt-4",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    assert response.summary_text == "Summary"


# Template Model Tests

def test_template_field():
    """Test template field creation."""
    field = TemplateField(
        name="email",
        type="string",
        required=True,
        description="Email address"
    )
    assert field.name == "email"
    assert field.required is True


def test_template_base_valid():
    """Test valid template base creation."""
    fields = [
        TemplateField(name="name", type="string", required=True),
        TemplateField(name="age", type="number", required=False)
    ]
    template = TemplateBase(
        name="User Template",
        description="Template for user data",
        fields=fields,
        is_public=True
    )
    assert template.name == "User Template"
    assert len(template.fields) == 2
    assert template.is_public is True


def test_template_base_empty_fields():
    """Test template with empty fields list."""
    with pytest.raises(ValidationError) as exc_info:
        TemplateBase(
            name="Empty Template",
            fields=[]
        )
    assert "must have at least one field" in str(exc_info.value)


def test_template_base_name_too_long():
    """Test template with name exceeding max length."""
    field = TemplateField(name="field", type="string")
    with pytest.raises(ValidationError) as exc_info:
        TemplateBase(
            name="a" * 101,
            fields=[field]
        )
    assert "at most 100 characters" in str(exc_info.value)


def test_template_create_valid():
    """Test valid template creation."""
    fields = [TemplateField(name="title", type="string")]
    template = TemplateCreate(
        user_id=str(ObjectId()),
        name="Document Template",
        fields=fields
    )
    assert template.name == "Document Template"


def test_template_create_invalid_user_id():
    """Test template create with invalid user ID."""
    fields = [TemplateField(name="field", type="string")]
    with pytest.raises(ValidationError) as exc_info:
        TemplateCreate(
            user_id="not-valid",
            name="Template",
            fields=fields
        )
    assert "Invalid ObjectId" in str(exc_info.value)


def test_template_update():
    """Test template update schema."""
    update = TemplateUpdate(
        name="Updated Template",
        is_public=False
    )
    assert update.name == "Updated Template"
    assert update.is_public is False


def test_template_update_partial():
    """Test partial template update."""
    update = TemplateUpdate(description="New description")
    assert update.description == "New description"
    assert update.name is None


def test_template_in_db():
    """Test template in database schema."""
    fields = [TemplateField(name="field", type="string")]
    template = TemplateInDB(
        user_id=ObjectId(),
        name="Template",
        fields=fields
    )
    assert template.id is not None
    assert isinstance(template.created_at, datetime)
    assert isinstance(template.updated_at, datetime)


def test_template_response():
    """Test template API response schema."""
    fields = [TemplateField(name="field", type="string")]
    response = TemplateResponse(
        id=str(ObjectId()),
        user_id=str(ObjectId()),
        name="Template",
        fields=fields,
        is_public=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    assert response.name == "Template"
    assert len(response.fields) == 1
