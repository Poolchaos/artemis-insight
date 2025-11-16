"""
Models package - exports all Pydantic models.
"""

from app.models.user import (
    PyObjectId,
    UserBase,
    UserCreate,
    UserInDB,
    UserResponse,
    TokenResponse,
    TokenPayload
)

from app.models.document import (
    DocumentStatus,
    DocumentBase,
    DocumentCreate,
    DocumentUpdate,
    DocumentInDB,
    DocumentResponse
)

from app.models.job import (
    JobType,
    JobStatus,
    JobBase,
    JobCreate,
    JobUpdate,
    JobInDB,
    JobResponse
)

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

from app.models.embedding import (
    EmbeddingBase,
    EmbeddingCreate,
    EmbeddingInDB,
    EmbeddingResponse,
    EmbeddingSearchQuery,
    EmbeddingSearchResult
)

from app.models.api_usage import (
    ApiUsageBase,
    ApiUsageCreate,
    ApiUsageInDB,
    ApiUsageResponse,
    ApiUsageStats
)

__all__ = [
    # User models
    "PyObjectId",
    "UserBase",
    "UserCreate",
    "UserInDB",
    "UserResponse",
    "TokenResponse",
    "TokenPayload",

    # Document models
    "DocumentStatus",
    "DocumentBase",
    "DocumentCreate",
    "DocumentUpdate",
    "DocumentInDB",
    "DocumentResponse",

    # Job models
    "JobType",
    "JobStatus",
    "JobBase",
    "JobCreate",
    "JobUpdate",
    "JobInDB",
    "JobResponse",

    # Summary models
    "SummaryBase",
    "SummaryCreate",
    "SummaryInDB",
    "SummaryResponse",
    "TemplateField",
    "TemplateBase",
    "TemplateCreate",
    "TemplateUpdate",
    "TemplateInDB",
    "TemplateResponse",

    # Embedding models
    "EmbeddingBase",
    "EmbeddingCreate",
    "EmbeddingInDB",
    "EmbeddingResponse",
    "EmbeddingSearchQuery",
    "EmbeddingSearchResult",

    # API Usage models
    "ApiUsageBase",
    "ApiUsageCreate",
    "ApiUsageInDB",
    "ApiUsageResponse",
    "ApiUsageStats",
]
