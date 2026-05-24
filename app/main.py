"""FastAPI application entry point.

Bootstraps the app, wiring is intentionally minimal for now: only app metadata
and a health check. Feature routers will be registered here as they are built.
"""

import logging

from fastapi import FastAPI

from app.infrastructure.config.settings import get_settings
from app.presentation.api.middleware.exception_handlers import (
    register_exception_handlers,
)
from app.presentation.api.v1.router import api_v1_router

settings = get_settings()


def create_app() -> FastAPI:
    """Application factory. Keeps app creation testable and import-safe."""
    # Ensure our INFO logs (e.g. simulated notifications) are visible.
    logging.basicConfig(level=logging.INFO)

    # Note: we intentionally do NOT pass debug=settings.debug. FastAPI/Starlette
    # debug mode returns raw tracebacks on 500s and bypasses our exception
    # handler — leaking internals. Our handler always returns a clean 500 instead.
    app = FastAPI(
        title="Fund Manager API",
        version="0.1.0",
    )

    @app.get("/health", tags=["health"])
    def health_check() -> dict[str, str]:
        """Liveness probe used by load balancers and deployment checks."""
        return {"status": "ok", "environment": settings.environment}

    # Versioned API routers. Each version owns its own prefix in code.
    app.include_router(api_v1_router)

    # Translate domain exceptions into HTTP responses.
    register_exception_handlers(app)

    return app


app = create_app()


# AWS Lambda entrypoint. Mangum adapts the ASGI app to the Lambda/API Gateway
# event-handler contract. Imported lazily so local/dev runs (and tests) never
# require mangum to be installed at import time of this module's other users.
def lambda_handler(event: dict, context: object) -> dict:  # pragma: no cover
    from mangum import Mangum

    return Mangum(app)(event, context)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        port=settings.port,
        reload=settings.debug,
    )
