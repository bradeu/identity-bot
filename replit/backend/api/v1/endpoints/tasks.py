from fastapi import APIRouter, HTTPException
from celery_app import celery_app
from models.response import TaskStatusResponse
from infra.logger import logger
from typing import Dict, Any

task_router = APIRouter(
    tags=["tasks"],
    responses={
        200: {"description": "Task status retrieved"},
        404: {"description": "Task not found"}
    }
)

@task_router.get("/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str) -> TaskStatusResponse:
    """
    Get the status of a Celery task.
    
    Args:
        task_id: The ID of the task to check
        
    Returns:
        TaskStatusResponse: Current status of the task
    """
    try:
        # Get task result
        task_result = celery_app.AsyncResult(task_id)
        
        # Check if task exists
        if not task_result.ready() and task_result.state == 'PENDING':
            # Check if task was never submitted
            if not hasattr(task_result, 'info') or task_result.info is None:
                raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        
        if task_result.state == 'PENDING':
            response = {
                'task_id': task_id,
                'status': 'PENDING',
                'message': 'Task is waiting to be processed'
            }
        elif task_result.state == 'STARTED':
            response = {
                'task_id': task_id,
                'status': 'STARTED',
                'message': 'Task has started processing'
            }
        elif task_result.state == 'PROGRESS':
            info = task_result.info or {}
            response = {
                'task_id': task_id,
                'status': 'PROGRESS',
                'message': info.get('status', 'Processing...'),
                'progress': info.get('progress', 0)
            }
        elif task_result.state == 'SUCCESS':
            response = {
                'task_id': task_id,
                'status': 'SUCCESS',
                'message': 'Task completed successfully',
                'result': task_result.result
            }
        elif task_result.state == 'FAILURE':
            error_info = task_result.info
            error_message = str(error_info) if error_info else 'Task failed'
            response = {
                'task_id': task_id,
                'status': 'FAILURE',
                'message': error_message,
                'error': error_message
            }
        elif task_result.state == 'RETRY':
            response = {
                'task_id': task_id,
                'status': 'RETRY',
                'message': 'Task is being retried'
            }
        elif task_result.state == 'REVOKED':
            response = {
                'task_id': task_id,
                'status': 'CANCELLED',
                'message': 'Task was cancelled'
            }
        else:
            response = {
                'task_id': task_id,
                'status': task_result.state,
                'message': f'Task is in {task_result.state} state'
            }
            
        logger.info(f"Task status requested for {task_id}: {response['status']}")
        return TaskStatusResponse(**response)
        
    except Exception as e:
        logger.error(f"Error retrieving task status for {task_id}: {str(e)}")
        raise HTTPException(
            status_code=404,
            detail=f"Task {task_id} not found or error occurred: {str(e)}"
        )

@task_router.delete("/cancel/{task_id}")
async def cancel_task(task_id: str) -> Dict[str, str]:
    """
    Cancel a Celery task.
    
    Args:
        task_id: The ID of the task to cancel
        
    Returns:
        Dict with cancellation status
    """
    try:
        celery_app.control.revoke(task_id, terminate=True)
        logger.info(f"Task {task_id} cancelled")
        return {"message": f"Task {task_id} has been cancelled"}
        
    except Exception as e:
        logger.error(f"Error cancelling task {task_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error cancelling task {task_id}: {str(e)}"
        )