import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI, UploadFile
import io
from datetime import datetime, timezone

from api.v1.api import api_router
from models.request import ProcessorRequest, QueryRequest
from models.response import (
    APIResponse, HealthResponse, ProcessorResponse, 
    DashboardResponse, QueryResponse, TaskStatusResponse
)


@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(api_router, prefix="/api/v1")
    return app


@pytest.fixture
def client(app):
    with TestClient(app) as client:
        yield client


@pytest.fixture
def sample_processor_request():
    return ProcessorRequest(
        pdf_path="/path/to/test.pdf",
        txt_path="/path/to/output.txt"
    )


@pytest.fixture
def sample_query_request():
    return QueryRequest(
        query="What is the party's stance on healthcare?",
        country="Canada",
        top_k=5
    )


class TestRootEndpoint:
    
    def test_v1_root_success(self, client):
        response = client.get("/api/v1/")
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["message"] == "Welcome to API v1"
        assert response_data["data"]["version"] == "1.0.0"
        assert response_data["data"]["status"] == "active"
        
        # Validate response model
        api_response = APIResponse(**response_data)
        assert api_response.message == "Welcome to API v1"


class TestHealthEndpoints:
    
    @patch('dependencies.get_health_check_service')
    def test_health_check_success(self, mock_get_service, client):
        # Setup
        mock_service = Mock()
        mock_health_response = HealthResponse(
            overall_status="healthy",
            service_status={
                "api": "healthy",
                "chroma": "healthy",
                "mongo": "healthy",
                "redis": "healthy",
                "celery": "healthy"
            },
            timestamp=datetime.now(timezone.utc),
            details={"service": "api", "response": "pong"}
        )
        mock_service.pong.return_value = mock_health_response
        mock_get_service.return_value = mock_service
        
        # Execute
        response = client.get("/api/v1/health/ping")
        
        # Verify
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["overall_status"] == "healthy"
        assert response_data["service_status"]["api"] == "healthy"
        assert "timestamp" in response_data
        
        # Validate response model
        health_response = HealthResponse(**response_data)
        assert health_response.overall_status == "healthy"
    
    @patch('dependencies.get_health_check_service')
    def test_health_check_degraded(self, mock_get_service, client):
        # Setup
        mock_service = Mock()
        mock_health_response = HealthResponse(
            overall_status="degraded",
            service_status={
                "api": "healthy",
                "chroma": "unhealthy",
                "mongo": "healthy",
                "redis": "unhealthy",
                "celery": "healthy"
            },
            timestamp=datetime.now(timezone.utc),
            details={"service": "api", "response": "pong"}
        )
        mock_service.pong.return_value = mock_health_response
        mock_get_service.return_value = mock_service
        
        # Execute
        response = client.get("/api/v1/health/ping")
        
        # Verify
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["overall_status"] == "degraded"
        assert response_data["service_status"]["chroma"] == "unhealthy"
    
    @patch('dependencies.get_health_check_service')
    def test_health_check_service_error(self, mock_get_service, client):
        # Setup
        mock_service = Mock()
        mock_service.pong.side_effect = Exception("Health check failed")
        mock_get_service.return_value = mock_service
        
        # Execute
        response = client.get("/api/v1/health/ping")
        
        # Verify
        assert response.status_code == 503
        response_data = response.json()
        assert response_data["detail"] == "Service unhealthy"


class TestProcessorEndpoints:
    
    @patch('api.v1.endpoints.processor.pdf_to_txt_task')
    def test_processor_pdf_success(self, mock_task, client, sample_processor_request):
        # Setup
        mock_celery_task = Mock()
        mock_celery_task.id = "test-task-id-123"
        mock_task.delay.return_value = mock_celery_task
        
        # Execute
        response = client.post(
            "/api/v1/processor/pdf",
            json=sample_processor_request.model_dump()
        )
        
        # Verify
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["task_id"] == "test-task-id-123"
        assert response_data["status"] == "success"
        
        # Validate response model
        processor_response = ProcessorResponse(**response_data)
        assert processor_response.task_id == "test-task-id-123"
        
        mock_task.delay.assert_called_once_with(
            pdf_path=sample_processor_request.pdf_path,
            output_path=sample_processor_request.txt_path
        )
    
    @patch('api.v1.endpoints.processor.pdf_to_txt_task')
    def test_processor_pdf_task_failure(self, mock_task, client, sample_processor_request):
        # Setup
        mock_task.delay.side_effect = Exception("Celery connection failed")
        
        # Execute
        response = client.post(
            "/api/v1/processor/pdf",
            json=sample_processor_request.model_dump()
        )
        
        # Verify
        assert response.status_code == 503
        response_data = response.json()
        assert response_data["detail"] == "Service unhealthy"
    
    def test_processor_pdf_invalid_request(self, client):
        # Invalid request missing txt_path
        invalid_request = {"pdf_path": "/path/to/test.pdf"}
        
        response = client.post("/api/v1/processor/pdf", json=invalid_request)
        
        assert response.status_code == 422  # Validation error
    
    @patch('api.v1.endpoints.processor.dashboard_task')
    def test_processor_pdf_dashboard_success(self, mock_task, client):
        # Setup
        mock_celery_task = Mock()
        mock_celery_task.id = "dashboard-task-id-456"
        mock_task.delay.return_value = mock_celery_task
        
        pdf_content = b"fake pdf content"
        files = {"file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")}
        data = {"filename": "custom_name.pdf", "country": "Germany"}
        
        # Execute
        response = client.post("/api/v1/processor/pdf/dashboard/", files=files, data=data)
        
        # Verify
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["task_id"] == "dashboard-task-id-456"
        assert response_data["status"] == "success"
        
        # Validate response model
        dashboard_response = DashboardResponse(**response_data)
        assert dashboard_response.task_id == "dashboard-task-id-456"
        
        mock_task.delay.assert_called_once_with(
            pdf_content=pdf_content,
            filename="custom_name.pdf",
            country="Germany"
        )
    
    @patch('api.v1.endpoints.processor.dashboard_task')
    def test_processor_pdf_dashboard_default_country(self, mock_task, client):
        # Setup
        mock_celery_task = Mock()
        mock_celery_task.id = "dashboard-task-id-789"
        mock_task.delay.return_value = mock_celery_task
        
        pdf_content = b"fake pdf content"
        files = {"file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")}
        
        # Execute
        response = client.post("/api/v1/processor/pdf/dashboard/", files=files)
        
        # Verify
        assert response.status_code == 200
        mock_task.delay.assert_called_once_with(
            pdf_content=pdf_content,
            filename="test.pdf",
            country="Canada"  # Default country
        )
    
    def test_processor_pdf_dashboard_missing_file(self, client):
        response = client.post("/api/v1/processor/pdf/dashboard/")
        
        assert response.status_code == 422  # Validation error for missing file


class TestQueryEndpoints:
    
    @patch('dependencies.get_query_service')
    def test_query_ask_success(self, mock_get_service, client, sample_query_request):
        # Setup
        mock_service = Mock()
        mock_query_result = {
            "answer": "The party supports universal healthcare coverage with increased funding.",
            "confidence": "high",
            "context": "Healthcare policy context..."
        }
        mock_service.query.return_value = mock_query_result
        mock_get_service.return_value = mock_service
        
        # Execute
        response = client.post(
            "/api/v1/query/ask",
            json=sample_query_request.model_dump()
        )
        
        # Verify
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["message"] == "Query successful"
        assert response_data["data"]["answer"] == "The party supports universal healthcare coverage with increased funding."
        assert response_data["status"] == "success"
        
        # Validate response model
        query_response = QueryResponse(**response_data)
        assert query_response.message == "Query successful"
        
        mock_service.query.assert_called_once_with(
            sample_query_request.query,
            sample_query_request.country,
            sample_query_request.top_k
        )
    
    @patch('dependencies.get_query_service')
    def test_query_ask_service_error(self, mock_get_service, client, sample_query_request):
        # Setup
        mock_service = Mock()
        mock_service.query.side_effect = Exception("Query processing failed")
        mock_get_service.return_value = mock_service
        
        # Execute
        response = client.post(
            "/api/v1/query/ask",
            json=sample_query_request.model_dump()
        )
        
        # Verify
        assert response.status_code == 503
        response_data = response.json()
        assert response_data["detail"] == "Service unhealthy"
    
    def test_query_ask_invalid_request(self, client):
        # Invalid request missing query
        invalid_request = {"country": "Canada", "top_k": 5}
        
        response = client.post("/api/v1/query/ask", json=invalid_request)
        
        assert response.status_code == 422  # Validation error
    
    def test_query_ask_empty_query(self, client):
        # Empty query string
        invalid_request = {"query": "", "country": "Canada", "top_k": 3}
        
        response = client.post("/api/v1/query/ask", json=invalid_request)
        
        # This should pass validation but might fail at service level
        assert response.status_code in [200, 503]


class TestTaskEndpoints:
    
    @patch('api.v1.endpoints.tasks.celery_app')
    def test_get_task_status_pending(self, mock_celery_app, client):
        # Setup
        mock_result = Mock()
        mock_result.ready.return_value = False
        mock_result.state = 'PENDING'
        mock_result.info = None
        mock_celery_app.AsyncResult.return_value = mock_result
        
        task_id = "test-task-123"
        
        # Execute
        response = client.get(f"/api/v1/tasks/status/{task_id}")
        
        # Verify
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["task_id"] == task_id
        assert response_data["status"] == "PENDING"
        assert response_data["message"] == "Task is waiting to be processed"
        
        # Validate response model
        task_response = TaskStatusResponse(**response_data)
        assert task_response.task_id == task_id
    
    @patch('api.v1.endpoints.tasks.celery_app')
    def test_get_task_status_success(self, mock_celery_app, client):
        # Setup
        mock_result = Mock()
        mock_result.ready.return_value = True
        mock_result.state = 'SUCCESS'
        mock_result.result = {"output_path": "/path/to/output.txt", "success": True}
        mock_celery_app.AsyncResult.return_value = mock_result
        
        task_id = "test-task-success"
        
        # Execute
        response = client.get(f"/api/v1/tasks/status/{task_id}")
        
        # Verify
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["task_id"] == task_id
        assert response_data["status"] == "SUCCESS"
        assert response_data["message"] == "Task completed successfully"
        assert response_data["result"]["success"] is True
    
    @patch('api.v1.endpoints.tasks.celery_app')
    def test_get_task_status_failure(self, mock_celery_app, client):
        # Setup
        mock_result = Mock()
        mock_result.ready.return_value = True
        mock_result.state = 'FAILURE'
        mock_result.info = "File not found error"
        mock_celery_app.AsyncResult.return_value = mock_result
        
        task_id = "test-task-failed"
        
        # Execute
        response = client.get(f"/api/v1/tasks/status/{task_id}")
        
        # Verify
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["task_id"] == task_id
        assert response_data["status"] == "FAILURE"
        assert "File not found error" in response_data["message"]
        assert response_data["error"] == "File not found error"
    
    @patch('api.v1.endpoints.tasks.celery_app')
    def test_get_task_status_progress(self, mock_celery_app, client):
        # Setup
        mock_result = Mock()
        mock_result.ready.return_value = False
        mock_result.state = 'PROGRESS'
        mock_result.info = {"status": "Processing page 5/10", "progress": 50}
        mock_celery_app.AsyncResult.return_value = mock_result
        
        task_id = "test-task-progress"
        
        # Execute
        response = client.get(f"/api/v1/tasks/status/{task_id}")
        
        # Verify
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["task_id"] == task_id
        assert response_data["status"] == "PROGRESS"
        assert response_data["message"] == "Processing page 5/10"
        assert response_data["progress"] == 50
    
    @patch('api.v1.endpoints.tasks.celery_app')
    def test_get_task_status_not_found(self, mock_celery_app, client):
        # Setup
        mock_result = Mock()
        mock_result.ready.return_value = False
        mock_result.state = 'PENDING'
        mock_result.info = None
        mock_celery_app.AsyncResult.return_value = mock_result
        
        # Mock hasattr to return False (task never submitted)
        with patch('builtins.hasattr', return_value=False):
            task_id = "nonexistent-task"
            
            # Execute
            response = client.get(f"/api/v1/tasks/status/{task_id}")
            
            # Verify
            assert response.status_code == 404
            response_data = response.json()
            assert f"Task {task_id} not found" in response_data["detail"]
    
    @patch('api.v1.endpoints.tasks.celery_app')
    def test_get_task_status_revoked(self, mock_celery_app, client):
        # Setup
        mock_result = Mock()
        mock_result.ready.return_value = True
        mock_result.state = 'REVOKED'
        mock_celery_app.AsyncResult.return_value = mock_result
        
        task_id = "test-task-cancelled"
        
        # Execute
        response = client.get(f"/api/v1/tasks/status/{task_id}")
        
        # Verify
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["task_id"] == task_id
        assert response_data["status"] == "CANCELLED"
        assert response_data["message"] == "Task was cancelled"
    
    @patch('api.v1.endpoints.tasks.celery_app')
    def test_cancel_task_success(self, mock_celery_app, client):
        # Setup
        mock_control = Mock()
        mock_celery_app.control = mock_control
        
        task_id = "test-task-to-cancel"
        
        # Execute
        response = client.delete(f"/api/v1/tasks/cancel/{task_id}")
        
        # Verify
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["message"] == f"Task {task_id} has been cancelled"
        
        mock_control.revoke.assert_called_once_with(task_id, terminate=True)
    
    @patch('api.v1.endpoints.tasks.celery_app')
    def test_cancel_task_error(self, mock_celery_app, client):
        # Setup
        mock_control = Mock()
        mock_control.revoke.side_effect = Exception("Celery error")
        mock_celery_app.control = mock_control
        
        task_id = "test-task-error"
        
        # Execute
        response = client.delete(f"/api/v1/tasks/cancel/{task_id}")
        
        # Verify
        assert response.status_code == 500
        response_data = response.json()
        assert f"Error cancelling task {task_id}" in response_data["detail"]


class TestEndpointIntegration:
    
    def test_processor_to_task_status_flow(self, client):
        """Test the flow from processor submission to task status checking"""
        with patch('api.v1.endpoints.processor.pdf_to_txt_task') as mock_task, \
             patch('api.v1.endpoints.tasks.celery_app') as mock_celery_app:
            
            # Setup processor response
            mock_celery_task = Mock()
            mock_celery_task.id = "integration-task-123"
            mock_task.delay.return_value = mock_celery_task
            
            # Submit PDF processing task
            processor_request = {"pdf_path": "/test.pdf", "txt_path": "/output.txt"}
            proc_response = client.post("/api/v1/processor/pdf", json=processor_request)
            
            assert proc_response.status_code == 200
            task_id = proc_response.json()["task_id"]
            
            # Setup task status response
            mock_result = Mock()
            mock_result.ready.return_value = True
            mock_result.state = 'SUCCESS'
            mock_result.result = {"success": True, "output_path": "/output.txt"}
            mock_celery_app.AsyncResult.return_value = mock_result
            
            # Check task status
            status_response = client.get(f"/api/v1/tasks/status/{task_id}")
            
            assert status_response.status_code == 200
            status_data = status_response.json()
            assert status_data["task_id"] == task_id
            assert status_data["status"] == "SUCCESS"
    
    def test_health_check_response_format(self, client):
        """Test that health check returns properly formatted timestamp"""
        with patch('dependencies.get_health_check_service') as mock_get_service:
            mock_service = Mock()
            test_timestamp = datetime.now(timezone.utc)
            mock_health_response = HealthResponse(
                overall_status="healthy",
                service_status={"api": "healthy"},
                timestamp=test_timestamp,
                details={"service": "api", "response": "pong"}
            )
            mock_service.pong.return_value = mock_health_response
            mock_get_service.return_value = mock_service
            
            response = client.get("/api/v1/health/ping")
            
            assert response.status_code == 200
            response_data = response.json()
            
            # Verify timestamp format
            assert "timestamp" in response_data
            # Should be ISO format with timezone
            timestamp_str = response_data["timestamp"]
            parsed_timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            assert parsed_timestamp.tzinfo is not None