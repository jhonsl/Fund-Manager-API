"""Aggregator router for API version 1.

The ``/api/v1`` prefix is defined here, in code, because the API version is an
intrinsic property of this module — it does not change between environments.
Feature routers (funds, transactions, ...) are included here as they are built.
"""

from fastapi import APIRouter

api_v1_router = APIRouter(prefix="/api/v1")

# Feature routers will be registered here, e.g.:
# from app.presentation.api.v1.routes import funds
# api_v1_router.include_router(funds.router)
