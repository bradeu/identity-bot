from datetime import datetime, timezone
from models.response import HealthResponse
# from infra.mongo import get_mongo_client  # Commented out MongoDB
from celery_app import celery_app
import redis
from config.config import get_settings
from db.pinecone_db import PineconeDB


class HealthCheckService:

    def __init__(self):
        self.settings = get_settings()

    def _check_redis(self):
        """Check Redis connection"""
        try:
            redis_client = redis.Redis.from_url(
                self.settings.CELERY_BROKER_URL)
            redis_client.ping()
            return "healthy"
        except Exception:
            return "unhealthy"

    # def _check_mongo(self):
    #     """Check MongoDB connection"""
    #     try:
    #         with get_mongo_client() as client:
    #             client.admin.command('ping')
    #         return "healthy"
    #     except Exception as e:
    #         print(f"MongoDB health check failed: {e}")
    #         print(
    #             f"MongoDB URI being used: {self.settings.mongodb_connection_uri}"
    #         )
    #         return "unhealthy"

    def _check_pinecone(self):
        """Check Pinecone connection"""
        try:
            pinecone_db = PineconeDB(
                api_key=self.settings.PINECONE_API_KEY,
                index_name="rag-documents"
            )
            if pinecone_db.heartbeat():
                return "healthy"
            return "unhealthy"
        except Exception as e:
            print(f"Pinecone health check failed: {e}")
            return "unhealthy"

    def _check_celery(self):
        """Check Celery connection"""
        try:
            inspect = celery_app.control.inspect()
            stats = inspect.stats()
            if stats:
                return "healthy"
            return "unhealthy"
        except Exception:
            return "unhealthy"

    def pong(self):
        """
        Health check endpoint.

        Returns:
            HealthResponse: A response with the status of all services and the current timestamp.
        """
        service_status = {
            "api": "healthy",
            "pinecone": self._check_pinecone(),
            # "mongo": self._check_mongo(),  # Commented out MongoDB
            "redis": self._check_redis(),
            "celery": self._check_celery()
        }

        overall_status = "healthy" if all(
            status == "healthy"
            for status in service_status.values()) else "degraded"

        return HealthResponse(overall_status=overall_status,
                              service_status=service_status,
                              timestamp=datetime.now(timezone.utc),
                              details={
                                  "service": "api",
                                  "response": "pong"
                              })
