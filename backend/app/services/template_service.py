"""
Template service for managing document analysis templates.

Handles CRUD operations for templates and provides default templates.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException, status

from app.models.template import (
    TemplateCreate,
    TemplateUpdate,
    TemplateInDB,
    TemplateResponse,
    FEASIBILITY_STUDY_TEMPLATE,
    EXECUTIVE_SUMMARY_TEMPLATE
)


class TemplateService:
    """Service for managing document analysis templates."""

    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize template service.

        Args:
            db: MongoDB database instance
        """
        self.db = db
        self.collection = db.templates

    def _convert_template_for_response(self, template: Dict[str, Any]) -> Dict[str, Any]:
        """Convert MongoDB document to TemplateResponse-compatible dict."""
        if template:
            template["_id"] = str(template["_id"])
            if template.get("created_by"):
                template["created_by"] = str(template["created_by"])
            if template.get("updated_by"):
                template["updated_by"] = str(template["updated_by"])
        return template

    async def create_template(
        self,
        template_data: TemplateCreate,
        created_by: str
    ) -> TemplateResponse:
        """
        Create a new template.

        Args:
            template_data: Template creation data
            created_by: User ID of creator

        Returns:
            Created template

        Raises:
            ValidationException: If template with same name exists
        """
        # Check if template with same name exists
        existing = await self.collection.find_one({
            "name": template_data.name,
            "is_active": True
        })
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Template with name '{template_data.name}' already exists"
            )

        # Create template document
        now = datetime.now(timezone.utc)
        template_dict = template_data.model_dump()
        template_dict.update({
            "_id": ObjectId(),
            "created_by": ObjectId(created_by),
            "created_at": now,
            "updated_at": now,
            "is_active": True,
            "usage_count": 0,
            "version": 1
        })

        # Insert into database
        result = await self.collection.insert_one(template_dict)

        # Fetch and return created template
        created = await self.collection.find_one({"_id": result.inserted_id})
        return TemplateResponse(**self._convert_template_for_response(created))

    async def get_template(self, template_id: str) -> TemplateResponse:
        """
        Get a template by ID.

        Args:
            template_id: Template ID

        Returns:
            Template data

        Raises:
            NotFoundException: If template not found
        """
        template = await self.collection.find_one({
            "_id": ObjectId(template_id),
            "is_active": True
        })

        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template with ID {template_id} not found"
            )

        return TemplateResponse(**self._convert_template_for_response(template))

    async def list_templates(
        self,
        skip: int = 0,
        limit: int = 100,
        category: Optional[str] = None
    ) -> List[TemplateResponse]:
        """
        List all active templates.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            category: Optional category filter

        Returns:
            List of templates
        """
        query: Dict[str, Any] = {"is_active": True}
        if category:
            query["category"] = category

        cursor = self.collection.find(query).skip(skip).limit(limit).sort("name", 1)
        templates = await cursor.to_list(length=limit)

        return [TemplateResponse(**self._convert_template_for_response(t)) for t in templates]

    async def update_template(
        self,
        template_id: str,
        template_data: TemplateUpdate,
        updated_by: str
    ) -> TemplateResponse:
        """
        Update a template.

        Args:
            template_id: Template ID
            template_data: Updated template data
            updated_by: User ID making the update

        Returns:
            Updated template

        Raises:
            NotFoundException: If template not found
        """
        # Check if template exists
        existing = await self.collection.find_one({
            "_id": ObjectId(template_id),
            "is_active": True
        })
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template with ID {template_id} not found"
            )

        # Prepare update data
        update_dict = template_data.model_dump(exclude_unset=True)
        update_dict.update({
            "updated_at": datetime.now(timezone.utc),
            "updated_by": ObjectId(updated_by),
            "version": existing.get("version", 1) + 1
        })

        # Update in database
        await self.collection.update_one(
            {"_id": ObjectId(template_id)},
            {"$set": update_dict}
        )

        # Fetch and return updated template
        updated = await self.collection.find_one({"_id": ObjectId(template_id)})
        return TemplateResponse(**self._convert_template_for_response(updated))

    async def delete_template(self, template_id: str, deleted_by: str) -> bool:
        """
        Soft delete a template (set is_active to False).

        Args:
            template_id: Template ID
            deleted_by: User ID performing deletion

        Returns:
            True if deleted successfully

        Raises:
            NotFoundException: If template not found
        """
        result = await self.collection.update_one(
            {"_id": ObjectId(template_id), "is_active": True},
            {
                "$set": {
                    "is_active": False,
                    "updated_at": datetime.now(timezone.utc),
                    "updated_by": ObjectId(deleted_by)
                }
            }
        )

        if result.matched_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template with ID {template_id} not found"
            )

        return True

    async def get_default_templates(self) -> List[TemplateResponse]:
        """
        Get all default system templates.

        Returns:
            List of default templates
        """
        cursor = self.collection.find({
            "is_default": True,
            "is_active": True
        }).sort("name", 1)

        templates = await cursor.to_list(length=None)
        return [TemplateResponse(**self._convert_template_for_response(t)) for t in templates]

    async def seed_default_templates(self, created_by: str) -> Dict[str, str]:
        """
        Seed the database with default templates if they don't exist.

        Args:
            created_by: User ID of system admin seeding templates

        Returns:
            Dictionary mapping template names to their IDs
        """
        seeded_templates = {}
        default_templates = [
            FEASIBILITY_STUDY_TEMPLATE,
            EXECUTIVE_SUMMARY_TEMPLATE
        ]

        for template_data in default_templates:
            # Check if already exists
            existing = await self.collection.find_one({
                "name": template_data.name,
                "is_default": True
            })

            if existing:
                # Update if exists
                seeded_templates[template_data.name] = str(existing["_id"])
                continue

            # Create new default template
            now = datetime.now(timezone.utc)
            template_dict = template_data.model_dump()
            template_dict.update({
                "_id": ObjectId(),
                "created_by": ObjectId(created_by),
                "created_at": now,
                "updated_at": now,
                "is_active": True,
                "is_default": True,
                "version": 1,
                "usage_count": 0
            })

            result = await self.collection.insert_one(template_dict)
            seeded_templates[template_data.name] = str(result.inserted_id)

        return seeded_templates

    async def get_template_by_name(self, name: str) -> Optional[TemplateResponse]:
        """
        Get a template by its name.

        Args:
            name: Template name

        Returns:
            Template if found, None otherwise
        """
        template = await self.collection.find_one({
            "name": name,
            "is_active": True
        })

        if template:
            return TemplateResponse(**self._convert_template_for_response(template))
        return None
