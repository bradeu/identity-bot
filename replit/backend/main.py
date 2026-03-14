from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from fastapi.staticfiles import StaticFiles
import openai
from api.v1.api import api_router
from config.config import get_settings
from infra.logger import logger
from infra.timing import TimingMiddleware
import base64
import os
# PostgreSQL imports
from models.sql import Base

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def custom_jsonable_encoder(obj, **kwargs):
    """Custom encoder that handles bytes by encoding them as base64"""
    if isinstance(obj, bytes):
        return base64.b64encode(obj).decode('utf-8')
    return jsonable_encoder(obj, **kwargs)


def create_app():
    settings = get_settings()

    app = FastAPI(title=settings.PROJECT_NAME,
                  description=settings.DESCRIPTION,
                  version=settings.VERSION,
                  docs_url="/docs" if settings.ENABLE_SWAGGER else None,
                  redoc_url="/redoc" if settings.ENABLE_REDOC else None)

    @app.on_event("startup")
    async def startup_event():
        """Initialize Pinecone connection at app startup"""
        try:
            logger.info("Initializing Pinecone connection at startup...")
            from dependencies import get_vector_db, get_embedding_function
            get_vector_db()
            get_embedding_function()
            logger.info("Pinecone and OpenAI embeddings initialized successfully")
            
            # Initialize PostgreSQL in background to avoid blocking port opening
            import asyncio
            asyncio.create_task(initialize_postgresql_background())
            
        except Exception as e:
            logger.error(f"Failed to initialize services at startup: {e}")
            raise

    async def initialize_postgresql_background():
        """Initialize PostgreSQL in background after app starts"""
        import anyio
        try:
            # Give the app a brief moment to start binding the port
            await anyio.sleep(2)

            logger.info("Background initialization: Initializing PostgreSQL...")
            from dependencies import get_db_client
            client = get_db_client()

            if hasattr(client, "test_connection") and callable(client.test_connection):
                ok = await anyio.to_thread.run_sync(client.test_connection)
            else:
                def _sync_test():
                    try:
                        with client.get_connection() as conn:
                            try:
                                conn.exec_driver_sql("SELECT 1")
                            except AttributeError:
                                with conn.cursor() as cur:
                                    cur.execute("SELECT 1")
                        return True
                    except Exception:
                        return False

                ok = await anyio.to_thread.run_sync(_sync_test)

            if ok:
                logger.info("Background initialization: PostgreSQL connection ready")
            else:
                logger.error("Background initialization: PostgreSQL connection failed")

        except Exception as e:
            logger.error(f"Background PostgreSQL initialization failed: {e}")

    # PostgreSQL shutdown
    @app.on_event("shutdown")
    async def on_shutdown():
        from dependencies import get_db_client
        get_db_client().dispose()

    app.add_middleware(TimingMiddleware)
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.get_allowed_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    

    app.mount("/chatbot",
              StaticFiles(directory=os.path.join(BASE_DIR,
                                                 "../frontend/build"),
                          html=True),
              name="frontend")
    app.mount("/dashboard",
              StaticFiles(directory=os.path.join(BASE_DIR, "../dashboard/out"),
                          html=True),
              name="dashboard")

    app.include_router(api_router, prefix=settings.API_V1_STR, tags=["v1"])

    openai.api_key = settings.OPENAI_API_KEY

    # Override the default JSON encoder to handle bytes
    import fastapi.encoders
    fastapi.encoders.jsonable_encoder = custom_jsonable_encoder

    logger.info("Application starting at %s", settings.PORT)

    return app


app = create_app()
