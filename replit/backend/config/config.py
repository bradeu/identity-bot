from typing import List, Optional, Union
from pydantic import validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import secrets
from functools import lru_cache


class Settings(BaseSettings):
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "FastAPI Backend"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "FastAPI backend for multilingual RAG"

    PORT: int = 8000

    # Security
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:27017,http://localhost:6379,http://localhost:5555,http://localhost:3001,http://localhost:3002"

    def get_allowed_origins(self) -> List[str]:
        """Parse ALLOWED_ORIGINS string into a list"""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    # Logging
    LOG_LEVEL: str = "DEBUG"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    PING_URL: str = "http://localhost:8000/api/v1/ping"

    # Feature Flags
    ENABLE_SWAGGER: bool = True
    ENABLE_REDOC: bool = True
    DEBUG: bool = False

    # OpenAI
    OPENAI_API_KEY: str
    EMBEDDING_MODEL: str = "text-embedding-ada-002"
    
    # Pinecone
    PINECONE_API_KEY: str
    PINECONE_INDEX_NAME: str = "bppl-rag"
    
    # PostgreSQL Database
    DB_HOST: str
    DB_PORT: int
    DB_DATABASE: str
    DB_USER: str
    DB_PASSWORD: str
    DB_POOL_MODE: Optional[str] = None
    DB_SSL_MODE: str = "prefer"  # Options: disable, allow, prefer, require, verify-ca, verify-full
    
    # MongoDB Atlas
    MONGO_URI: str = "mongodb://localhost:27017"  # Fallback for local development
    MONGO_DB: str = "multilingual_rag"
    MONGO_TIMEOUT: int = 5000

    # MongoDB Atlas specific settings
    MONGODB_ATLAS_URI: Optional[str] = None
    MONGODB_ATLAS_USERNAME: Optional[str] = None
    MONGODB_ATLAS_PASSWORD: Optional[str] = None
    MONGODB_ATLAS_CLUSTER: Optional[str] = None
    MONGODB_ATLAS_DATABASE: Optional[str] = None

    MAX_TURNS: int = 5

    @property
    def mongodb_connection_uri(self) -> str:
        """
        Returns MongoDB Atlas URI if configured, otherwise falls back to local MongoDB.
        """
        if self.MONGODB_ATLAS_URI:
            return self.MONGODB_ATLAS_URI
        elif all([
                self.MONGODB_ATLAS_USERNAME, self.MONGODB_ATLAS_PASSWORD,
                self.MONGODB_ATLAS_CLUSTER
        ]):
            # Construct MongoDB Atlas connection string
            return f"mongodb+srv://{self.MONGODB_ATLAS_USERNAME}:{self.MONGODB_ATLAS_PASSWORD}@{self.MONGODB_ATLAS_CLUSTER}/?retryWrites=true&w=majority"
        else:
            # Fallback to local MongoDB
            return self.MONGO_URI

    @property
    def mongodb_database_name(self) -> str:
        """
        Returns MongoDB Atlas database name if configured, otherwise falls back to local database name.
        """
        return self.MONGODB_ATLAS_DATABASE or self.MONGO_DB

    # Redis & Celery
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # Model configuration
    model_config = SettingsConfigDict(env_file=".env",
                                      env_file_encoding="utf-8",
                                      case_sensitive=True,
                                      extra="ignore")


@lru_cache()
def get_settings() -> Settings:
    """
    Returns cached settings instance.
    """
    return Settings()