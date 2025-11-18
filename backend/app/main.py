"""
FastAPI application initialization and configuration.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.database import db_manager, get_db
from app.routes import auth, documents, templates, summaries, jobs, batch
from app.services.template_service import TemplateService
from bson import ObjectId


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    await db_manager.connect()

    # Seed default templates
    try:
        db = db_manager.get_database()
        template_service = TemplateService(db)
        # Use a fixed system ObjectId for seeding
        system_user_id = str(ObjectId("000000000000000000000000"))
        await template_service.seed_default_templates(created_by=system_user_id)
        print("✅ Default templates seeded successfully")
    except Exception as e:
        print(f"⚠️ Warning: Could not seed templates: {e}")

    yield
    # Shutdown
    await db_manager.disconnect()


def create_application() -> FastAPI:
    """Create and configure FastAPI application."""

    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="AI-powered document intelligence platform",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan
    )

    # CORS middleware
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.debug else [
            "https://app.insights.artemisinnovations.co.za"
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition"],
    )

    # Register routers
    application.include_router(auth.router)
    application.include_router(documents.router)
    application.include_router(templates.router)
    application.include_router(summaries.router)
    application.include_router(jobs.router)
    application.include_router(batch.router)

    # Health check endpoint
    @application.get("/health")
    async def health_check():
        """Health check endpoint for Docker and monitoring."""
        return {
            "status": "healthy",
            "app": settings.app_name,
            "environment": settings.app_env
        }

    return application


app = create_application()
