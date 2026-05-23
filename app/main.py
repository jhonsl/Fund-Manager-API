"""FastAPI application entry point.

Bootstraps the app, wiring is intentionally minimal for now: only app metadata
and a health check. Feature routers will be registered here as they are built.
"""

from fastapi import FastAPI

from app.infrastructure.config.settings import get_settings
from app.presentation.api.v1.router import api_v1_router

settings = get_settings()


def create_app() -> FastAPI:
    """Application factory. Keeps app creation testable and import-safe."""
    app = FastAPI(
        title="Fund Manager API",
        version="0.1.0",
        debug=settings.debug,
    )

    @app.get("/health", tags=["health"])
    def health_check() -> dict[str, str]:
        """Liveness probe used by load balancers and deployment checks."""
        return {"status": "ok", "environment": settings.environment}

    # Versioned API routers. Each version owns its own prefix in code.
    app.include_router(api_v1_router)

    return app


app = create_app()
