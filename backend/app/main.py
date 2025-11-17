"""
FastAPI application initialization and configuration.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.database import db_manager
from app.routes import auth, documents, templates, summaries, jobs


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    await db_manager.connect()
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
