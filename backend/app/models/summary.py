"""
Summary and Template models for document extraction and processing results.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator

from app.models.user import PyObjectId


class SummaryBase(BaseModel):
    """Base summary schema."""
    summary_text: str = Field(..., min_length=1, description="Generated summary text")
    extraction_data: Optional[Dict[str, Any]] = Field(default=None, description="Extracted structured data")
    confidence_scores: Optional[Dict[str, float]] = Field(default=None, description="Confidence scores for extractions")
    model_used: str = Field(..., description="AI model used for generation")

    @field_validator('confidence_scores')
    @classmethod
    def validate_confidence_scores(cls, v: Optional[Dict[str, float]]) -> Optional[Dict[str, float]]:
        """Validate confidence scores are between 0 and 1."""
        if v is not None:
            for key, score in v.items():
                if not 0 <= score <= 1:
                    raise ValueError(f"Confidence score for '{key}' must be between 0 and 1")
        return v


class SummaryCreate(SummaryBase):
    """Schema for creating a new summary."""
    document_id: str = Field(..., description="Associated document ID")
    user_id: str = Field(..., description="User ID who owns the document")

    @field_validator('document_id', 'user_id')
    @classmethod
    def validate_object_ids(cls, v: str) -> str:
        """Validate IDs are valid ObjectIds."""
        PyObjectId.validate(v, None)
        return v


class SummaryInDB(SummaryBase):
    """Summary schema as stored in database."""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    document_id: PyObjectId = Field(..., description="Associated document ID")
    user_id: PyObjectId = Field(..., description="User ID")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {PyObjectId: str, datetime: lambda v: v.isoformat()}


class SummaryResponse(BaseModel):
    """Summary schema for API responses."""
    id: str = Field(..., description="Summary ID")
    document_id: str = Field(..., description="Document ID")
    user_id: str = Field(..., description="User ID")
    summary_text: str
    extraction_data: Optional[Dict[str, Any]] = None
    confidence_scores: Optional[Dict[str, float]] = None
    model_used: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat()}


# Template Models

class TemplateField(BaseModel):
    """Schema for a template field definition."""
    name: str = Field(..., description="Field name")
    type: str = Field(..., description="Field type (string, number, date, boolean)")
    required: bool = Field(default=False, description="Whether field is required")
    description: Optional[str] = Field(default=None, description="Field description")
    validation_rules: Optional[Dict[str, Any]] = Field(default=None, description="Validation rules")


class TemplateBase(BaseModel):
    """Base template schema."""
    name: str = Field(..., min_length=1, max_length=100, description="Template name")
    description: Optional[str] = Field(default=None, max_length=500, description="Template description")
    fields: List[TemplateField] = Field(..., description="Template field definitions")
    is_public: bool = Field(default=False, description="Whether template is public")

    @field_validator('fields')
    @classmethod
    def validate_fields(cls, v: List[TemplateField]) -> List[TemplateField]:
        """Validate template has at least one field."""
        if not v:
            raise ValueError("Template must have at least one field")
        return v


class TemplateCreate(TemplateBase):
    """Schema for creating a new template."""
    user_id: str = Field(..., description="User ID who created the template")

    @field_validator('user_id')
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        """Validate user_id is a valid ObjectId."""
        PyObjectId.validate(v, None)
        return v


class TemplateUpdate(BaseModel):
    """Schema for updating template fields."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    fields: Optional[List[TemplateField]] = None
    is_public: Optional[bool] = None


class TemplateInDB(TemplateBase):
    """Template schema as stored in database."""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId = Field(..., description="User ID who created the template")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {PyObjectId: str, datetime: lambda v: v.isoformat()}


class TemplateResponse(BaseModel):
    """Template schema for API responses."""
    id: str = Field(..., description="Template ID")
    user_id: str = Field(..., description="User ID")
    name: str
    description: Optional[str] = None
    fields: List[TemplateField]
    is_public: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat()}
