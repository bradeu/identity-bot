import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from service.healthcheck import HealthCheckService
from models.response import HealthResponse


class TestHealthCheckService:
    
    @pytest.fixture
    def health_service(self):
        with patch('service.healthcheck.get_settings') as mock_settings:
            mock_settings.return_value.CELERY_BROKER_URL = "redis://localhost:6379/0"
            return HealthCheckService()
    
    def test_init_loads_settings(self):
        with patch('service.healthcheck.get_settings') as mock_settings:
            mock_config = Mock()
            mock_config.CELERY_BROKER_URL = "redis://test:6379/0"
            mock_settings.return_value = mock_config
            
            service = HealthCheckService()
            
            mock_settings.assert_called_once()
            assert service.settings == mock_config
    
    @patch('service.healthcheck.redis.Redis')
    def test_check_redis_healthy(self, mock_redis_class, health_service):
        # Setup
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_redis_class.from_url.return_value = mock_client
        
        # Execute
        result = health_service._check_redis()
        
        # Verify
        assert result == "healthy"
        mock_redis_class.from_url.assert_called_once_with(health_service.settings.CELERY_BROKER_URL)
        mock_client.ping.assert_called_once()
    
    @patch('service.healthcheck.redis.Redis')
    def test_check_redis_unhealthy_connection_error(self, mock_redis_class, health_service):
        # Setup
        mock_client = Mock()
        mock_client.ping.side_effect = Exception("Connection failed")
        mock_redis_class.from_url.return_value = mock_client
        
        # Execute
        result = health_service._check_redis()
        
        # Verify
        assert result == "unhealthy"
        mock_redis_class.from_url.assert_called_once()
        mock_client.ping.assert_called_once()
    
    @patch('service.healthcheck.redis.Redis')
    def test_check_redis_unhealthy_from_url_error(self, mock_redis_class, health_service):
        # Setup
        mock_redis_class.from_url.side_effect = Exception("Invalid URL")
        
        # Execute
        result = health_service._check_redis()
        
        # Verify
        assert result == "unhealthy"
        mock_redis_class.from_url.assert_called_once()
    
    @patch('service.healthcheck.get_mongo_client')
    def test_check_mongo_healthy(self, mock_get_client, health_service):
        # Setup
        mock_client = Mock()
        mock_admin = Mock()
        mock_client.admin = mock_admin
        mock_admin.command.return_value = {"ok": 1}
        mock_get_client.return_value.__enter__.return_value = mock_client
        
        # Execute
        result = health_service._check_mongo()
        
        # Verify
        assert result == "healthy"
        mock_get_client.assert_called_once()
        mock_admin.command.assert_called_once_with('ping')
    
    @patch('service.healthcheck.get_mongo_client')
    def test_check_mongo_unhealthy(self, mock_get_client, health_service):
        # Setup
        mock_get_client.side_effect = Exception("MongoDB connection failed")
        
        # Execute
        result = health_service._check_mongo()
        
        # Verify
        assert result == "unhealthy"
        mock_get_client.assert_called_once()
    
    @patch('service.healthcheck.ChromaDB')
    @patch('service.healthcheck.BGEM3EmbeddingFunction')
    def test_check_chroma_healthy(self, mock_embedding, mock_chroma_class, health_service):
        # Setup
        mock_embedding_instance = Mock()
        mock_embedding.return_value = mock_embedding_instance
        
        mock_chroma = Mock()
        mock_chroma.heartbeat.return_value = True
        mock_chroma_class.return_value = mock_chroma
        
        # Execute
        result = health_service._check_chroma()
        
        # Verify
        assert result == "healthy"
        mock_chroma_class.assert_called_once_with(
            persist_directory="./chroma_db",
            embedding_function=mock_embedding_instance
        )
        mock_chroma.heartbeat.assert_called_once()
    
    @patch('service.healthcheck.ChromaDB')
    @patch('service.healthcheck.BGEM3EmbeddingFunction')
    def test_check_chroma_unhealthy(self, mock_embedding, mock_chroma_class, health_service):
        # Setup
        mock_chroma_class.side_effect = Exception("ChromaDB connection failed")
        
        # Execute
        result = health_service._check_chroma()
        
        # Verify
        assert result == "unhealthy"
        mock_chroma_class.assert_called_once()
    
    @patch('service.healthcheck.celery_app')
    def test_check_celery_healthy(self, mock_celery, health_service):
        # Setup
        mock_inspect = Mock()
        mock_stats = {"worker1": {"pool": {"max-concurrency": 4}}}
        mock_inspect.stats.return_value = mock_stats
        mock_celery.control.inspect.return_value = mock_inspect
        
        # Execute
        result = health_service._check_celery()
        
        # Verify
        assert result == "healthy"
        mock_celery.control.inspect.assert_called_once()
        mock_inspect.stats.assert_called_once()
    
    @patch('service.healthcheck.celery_app')
    def test_check_celery_unhealthy_no_stats(self, mock_celery, health_service):
        # Setup
        mock_inspect = Mock()
        mock_inspect.stats.return_value = None
        mock_celery.control.inspect.return_value = mock_inspect
        
        # Execute
        result = health_service._check_celery()
        
        # Verify
        assert result == "unhealthy"
    
    @patch('service.healthcheck.celery_app')
    def test_check_celery_unhealthy_empty_stats(self, mock_celery, health_service):
        # Setup
        mock_inspect = Mock()
        mock_inspect.stats.return_value = {}
        mock_celery.control.inspect.return_value = mock_inspect
        
        # Execute
        result = health_service._check_celery()
        
        # Verify
        assert result == "unhealthy"
    
    @patch('service.healthcheck.celery_app')
    def test_check_celery_unhealthy_exception(self, mock_celery, health_service):
        # Setup
        mock_celery.control.inspect.side_effect = Exception("Celery connection failed")
        
        # Execute
        result = health_service._check_celery()
        
        # Verify
        assert result == "unhealthy"
    
    def test_pong_all_services_healthy(self, health_service):
        # Setup - mock all check methods to return healthy
        with patch.object(health_service, '_check_chroma', return_value="healthy"), \
             patch.object(health_service, '_check_mongo', return_value="healthy"), \
             patch.object(health_service, '_check_redis', return_value="healthy"), \
             patch.object(health_service, '_check_celery', return_value="healthy"):
            
            # Execute
            result = health_service.pong()
            
            # Verify
            assert isinstance(result, HealthResponse)
            assert result.overall_status == "healthy"
            assert result.service_status == {
                "api": "healthy",
                "chroma": "healthy",
                "mongo": "healthy",
                "redis": "healthy",
                "celery": "healthy"
            }
            assert isinstance(result.timestamp, datetime)
            assert result.details == {"service": "api", "response": "pong"}
    
    def test_pong_some_services_unhealthy(self, health_service):
        # Setup - mock some services as unhealthy
        with patch.object(health_service, '_check_chroma', return_value="healthy"), \
             patch.object(health_service, '_check_mongo', return_value="unhealthy"), \
             patch.object(health_service, '_check_redis', return_value="healthy"), \
             patch.object(health_service, '_check_celery', return_value="unhealthy"):
            
            # Execute
            result = health_service.pong()
            
            # Verify
            assert isinstance(result, HealthResponse)
            assert result.overall_status == "degraded"
            assert result.service_status == {
                "api": "healthy",
                "chroma": "healthy",
                "mongo": "unhealthy",
                "redis": "healthy",
                "celery": "unhealthy"
            }
            assert isinstance(result.timestamp, datetime)
            assert result.details == {"service": "api", "response": "pong"}
    
    def test_pong_all_services_unhealthy(self, health_service):
        # Setup - mock all external services as unhealthy
        with patch.object(health_service, '_check_chroma', return_value="unhealthy"), \
             patch.object(health_service, '_check_mongo', return_value="unhealthy"), \
             patch.object(health_service, '_check_redis', return_value="unhealthy"), \
             patch.object(health_service, '_check_celery', return_value="unhealthy"):
            
            # Execute
            result = health_service.pong()
            
            # Verify
            assert isinstance(result, HealthResponse)
            assert result.overall_status == "degraded"
            assert result.service_status == {
                "api": "healthy",  # API itself is always healthy
                "chroma": "unhealthy",
                "mongo": "unhealthy",
                "redis": "unhealthy",
                "celery": "unhealthy"
            }
    
    def test_pong_timestamp_in_utc(self, health_service):
        # Setup
        with patch.object(health_service, '_check_chroma', return_value="healthy"), \
             patch.object(health_service, '_check_mongo', return_value="healthy"), \
             patch.object(health_service, '_check_redis', return_value="healthy"), \
             patch.object(health_service, '_check_celery', return_value="healthy"):
            
            # Execute
            result = health_service.pong()
            
            # Verify timestamp is UTC
            assert result.timestamp.tzinfo == timezone.utc
            # Verify timestamp is recent (within last minute)
            now = datetime.now(timezone.utc)
            time_diff = abs((now - result.timestamp).total_seconds())
            assert time_diff < 60  # Should be very recent