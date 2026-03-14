from typing import Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime

class APIResponse(BaseModel):
    """Base response model for API endpoints"""
    message: str
    data: Dict[str, Any] = {}
    status: str = "success"

class HealthResponse(BaseModel):
    """Health check response model"""
    overall_status: str = "success"
    service_status: Dict[str, Any] = {}
    timestamp: datetime
    details: Dict[str, Any] = {}

class ProcessorResponse(BaseModel):
    """Processor response model"""
    task_id: str
    status: str = "success"

class IngestionResponse(BaseModel):
    """Ingestion response model"""
    task_id: str
    status: str = "success"

class QueryResponse(BaseModel):
    """Query response model"""
    message: str
    data: Dict[str, Any] = {}
    status: str = "success"

class TaskStatusResponse(BaseModel):
    """Task status response model"""
    task_id: str
    status: str
    message: str
    progress: Optional[int] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class DashboardResponse(BaseModel):
    """Dashboard response model"""
    task_id: str
    status: str = "success"