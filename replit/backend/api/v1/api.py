from fastapi import APIRouter
from models.response import APIResponse
from api.v1.endpoints.health import health_check_router
from api.v1.endpoints.processor import processor_router
from api.v1.endpoints.query import query_router
from api.v1.endpoints.tasks import task_router
from api.v1.endpoints.persistence import persistence_router


api_router = APIRouter(
    tags=["v1"],
    responses={
        404: {"description": "Not found"},
        500: {"description": "Internal server error"}
    }
)

@api_router.get("/", response_model=APIResponse)
async def v1_root():
    """
    Root endpoint for API v1
    
    Returns:
        APIResponse: Basic API information
    """
    return APIResponse(
        message="Welcome to API v1",
        data={"version": "1.0.0", "status": "active"}
    )

api_router.include_router(
    health_check_router,
    prefix="/health",
    tags=["health"],
    responses={
        200: {"description": "Health check successful"},
        503: {"description": "Service unhealthy"}
    }
)

api_router.include_router(
    processor_router,
    prefix="/processor",
    tags=["processor"],
    responses={
        200: {"description": "Processor successful"},
        503: {"description": "Processor failed"}
    }
)


api_router.include_router(
    query_router,
    prefix="/query",
    tags=["query"],
    responses={
        200: {"description": "Query successful"},
        503: {"description": "Query failed"}
    }
)

api_router.include_router(
    task_router,
    prefix="/tasks",
    tags=["tasks"],
    responses={
        200: {"description": "Task operation successful"},
        404: {"description": "Task not found"}
    }
)

api_router.include_router(
    persistence_router,
    prefix="/persistence",
    tags=["persistence"],
    responses={
        200: {"description": "Persistence operation successful"},
        500: {"description": "Persistence operation failed"}
    }
)