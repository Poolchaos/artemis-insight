"""
Template API endpoints for managing document analysis templates.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.template import TemplateCreate, TemplateUpdate, TemplateResponse
from app.services.template_service import TemplateService
from app.middleware.auth import get_current_user, get_current_admin_user
from app.models.user import UserInDB
from app.database import get_db


router = APIRouter(prefix="/api/templates", tags=["templates"])


def get_template_service(db: AsyncIOMotorDatabase = Depends(get_db)) -> TemplateService:
    """Dependency to get template service instance."""
    return TemplateService(db)


@router.post("", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    template_data: TemplateCreate,
    current_user: UserInDB = Depends(get_current_admin_user),
    template_service: TemplateService = Depends(get_template_service)
):
    """
    Create a new template. Admin only.

    Creates a new document analysis template with sections, processing strategy,
    and guidance prompts for AI summarization.

    **Permissions:** Admin only
    """
    return await template_service.create_template(
        template_data=template_data,
        created_by=str(current_user.id)
    )


@router.get("", response_model=List[TemplateResponse])
async def list_templates(
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=100, ge=1, le=100, description="Max records to return"),
    category: Optional[str] = Query(default=None, description="Filter by category"),
    current_user: UserInDB = Depends(get_current_user),
    template_service: TemplateService = Depends(get_template_service)
):
    """
    List all active templates.

    Returns a paginated list of all available document analysis templates.
    Users can see all templates to select from when processing documents.

    **Permissions:** Any authenticated user
    """
    return await template_service.list_templates(
        skip=skip,
        limit=limit,
        category=category
    )


@router.get("/defaults", response_model=List[TemplateResponse])
async def get_default_templates(
    current_user: UserInDB = Depends(get_current_user),
    template_service: TemplateService = Depends(get_template_service)
):
    """
    Get all default system templates.

    Returns pre-configured templates like:
    - Feasibility Study Summary (9 sections)
    - Executive Summary (3 sections)

    **Permissions:** Any authenticated user
    """
    return await template_service.get_default_templates()


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: str,
    current_user: UserInDB = Depends(get_current_user),
    template_service: TemplateService = Depends(get_template_service)
):
    """
    Get a specific template by ID.

    Returns detailed information about a template including:
    - All sections with guidance prompts
    - Processing strategy and AI parameters
    - System prompts and configuration

    **Permissions:** Any authenticated user
    """
    return await template_service.get_template(template_id)


@router.put("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: str,
    template_data: TemplateUpdate,
    current_user: UserInDB = Depends(get_current_admin_user),
    template_service: TemplateService = Depends(get_template_service)
):
    """
    Update a template. Admin only.

    Updates template configuration including sections, prompts, and processing strategy.
    Version number is automatically incremented on each update.

    **Permissions:** Admin only
    """
    return await template_service.update_template(
        template_id=template_id,
        template_data=template_data,
        updated_by=str(current_user.id)
    )


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: str,
    current_user: UserInDB = Depends(get_current_admin_user),
    template_service: TemplateService = Depends(get_template_service)
):
    """
    Delete a template (soft delete). Admin only.

    Sets the template's is_active flag to False. The template remains
    in the database but won't appear in listings or be selectable.

    **Permissions:** Admin only
    """
    await template_service.delete_template(
        template_id=template_id,
        deleted_by=str(current_user.id)
    )
    return None


@router.post("/seed", response_model=dict, status_code=status.HTTP_201_CREATED)
async def seed_default_templates(
    current_user: UserInDB = Depends(get_current_admin_user),
    template_service: TemplateService = Depends(get_template_service)
):
    """
    Seed database with default templates. Admin only.

    Creates or updates the following default templates:
    - Feasibility Study Summary (9 sections)
    - Executive Summary (3 sections)

    This endpoint is idempotent - it won't create duplicates if templates
    already exist.

    **Permissions:** Admin only
    """
    seeded = await template_service.seed_default_templates(
        created_by=str(current_user.id)
    )

    return {
        "message": "Default templates seeded successfully",
        "templates": seeded
    }
