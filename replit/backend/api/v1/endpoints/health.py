from fastapi import APIRouter, HTTPException
from models.response import HealthResponse
from fastapi import Depends
from dependencies import get_health_check_service

health_check_router = APIRouter(
    tags=["health"],
    responses={
        200: {"description": "Health check successful"},
        503: {"description": "Service unhealthy"}
    }
)

@health_check_router.get("/ping", response_model=HealthResponse)
async def health_check(service = Depends(get_health_check_service)):
    """
    Health check endpoint
    
    Returns:
        HealthResponse: Health status of the API
    """
    try:
        return service.pong()
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail="Service unhealthy",
            error=str(e)
        )