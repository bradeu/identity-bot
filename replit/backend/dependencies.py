from functools import lru_cache
from service.openai_embedder import OpenAIEmbeddingFunction
from db.pinecone_db import PineconeDB
from db.postgresql import SQLAsyncClient
from service.healthcheck import HealthCheckService
from service.ingestion import IngestionService
from service.csv_processor import CSVProcessor
from service.query import QueryService
from service.conversation import ConversationService
from service.summarizer import SummarizerService
from service.session import SessionService
from config.config import get_settings

@lru_cache()
def get_health_check_service():
    """
    Returns cached health check service instance.
    """
    return HealthCheckService()


@lru_cache()
def get_vector_db():
    """
    Returns cached Pinecone vector database instance.
    """
    settings = get_settings()
    pinecone_db = PineconeDB(
        api_key=settings.PINECONE_API_KEY,
        index_name=settings.PINECONE_INDEX_NAME
    )
    return pinecone_db

@lru_cache()
def get_db_client():
    """
    Returns cached SQL client instance.
    """
    settings = get_settings()
    sql_client = SQLAsyncClient(
        host=settings.DB_HOST, 
        port=settings.DB_PORT, 
        database=settings.DB_DATABASE, 
        user=settings.DB_USER, 
        password=settings.DB_PASSWORD, 
        pool_mode=settings.DB_POOL_MODE,
        ssl=settings.DB_SSL_MODE
    )
    return sql_client

@lru_cache()
def get_csv_processor_service():
    """
    Returns cached CSV processor service instance.
    """
    return CSVProcessor()

@lru_cache()
def get_embedding_function():
    """
    Returns cached OpenAI embedding function.
    """
    settings = get_settings()
    return OpenAIEmbeddingFunction(
        api_key=settings.OPENAI_API_KEY,
        model_name=settings.EMBEDDING_MODEL
    )

@lru_cache()
def get_ingestion_service():
    """
    Returns cached ingestion service instance.
    """
    return IngestionService(
        vector_db=get_vector_db(),
        embedding_function=get_embedding_function()
    )

@lru_cache()
def get_query_service():
    """
    Returns cached query service instance.
    """
    return QueryService(
        vector_db=get_vector_db(),
        embedding_function=get_embedding_function()
    )

@lru_cache()
def get_conversation_service():
    """
    Returns cached conversation service instance.
    """
    return ConversationService()

@lru_cache()
def get_summarizer_service():
    """
    Returns cached summarizer service instance.
    """
    return SummarizerService()

@lru_cache()
def get_session_service():
    """
    Returns cached session service instance.
    """
    return SessionService()