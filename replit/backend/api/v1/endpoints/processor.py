from fastapi import APIRouter, HTTPException, UploadFile, File
from models.response import DashboardResponse
from tasks.background_tasks import csv_task
from infra.logger import logger

processor_router = APIRouter(
    tags=["processor"],
    responses={
        200: {"description": "Processor successful"},
        503: {"description": "Service unhealthy"}
    }
)


@processor_router.post("/csv/dashboard/")
async def csv_dashboard(file: UploadFile = File(...)):
    """
    Accept a CSV upload from the dashboard and queue it for ingestion into PostgreSQL.

    Args:
        file: CSV file matching the party-support schema

    Returns:
        DashboardResponse with task_id for status polling
    """
    try:
        csv_content = await file.read()
        filename = file.filename or "upload.csv"

        task = csv_task.delay(csv_content=csv_content, filename=filename)

        logger.info(f"CSV ingestion task {task.id} submitted for file: {filename}")
        return DashboardResponse(task_id=task.id, status="success")
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
