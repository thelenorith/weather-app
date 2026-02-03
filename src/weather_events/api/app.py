"""FastAPI application factory.

Creates and configures the FastAPI application with all routes and middleware.

## Usage

```python
from weather_events.api import create_app

app = create_app()

# Run with uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Configuration

The app is configured via environment variables. See `weather_events.config`
for available settings.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from weather_events.config import get_settings
from weather_events.database.connection import close_db, init_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager.

    Handles startup and shutdown tasks:
    - Initialize database connection
    - Start background tasks
    - Clean up on shutdown
    """
    settings = get_settings()

    logger.info(f"Starting {settings.app_name} v{settings.app_version}")

    # Initialize database
    await init_db()

    yield

    # Shutdown
    logger.info("Shutting down")
    await close_db()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Weather-aware calendar event recommendations",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        openapi_url="/openapi.json" if settings.debug else None,
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["*"],
    )

    # Include routers
    from weather_events.api.routes import auth, calendars, settings as settings_routes, users

    app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
    app.include_router(users.router, prefix="/api/users", tags=["Users"])
    app.include_router(calendars.router, prefix="/api/calendars", tags=["Calendars"])
    app.include_router(settings_routes.router, prefix="/api/settings", tags=["Settings"])

    # Health check endpoint
    @app.get("/health", tags=["Health"])
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "version": settings.app_version}

    return app
