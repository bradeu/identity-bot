from typing import Optional, Dict, Any
from contextlib import contextmanager, asynccontextmanager
from sqlalchemy import create_engine, text, Engine
from sqlalchemy.pool import NullPool


class SQLAsyncClient:
    """
    Postgres client for FastAPI using SQLAlchemy + psycopg (v3).
    - Works perfectly with PgBouncer transaction pooling mode.
    - Uses NullPool to let PgBouncer handle connection pooling.
    - Simple and reliable with libpq SSL handling.

    Args:
        host: str
        port: int
        database: str
        user: str
        password: str
        pool_mode: Optional[str] = None
        ssl: str | bool = "require"
        statement_timeout_ms: int = 15000 (unused, for compatibility)
        connect_args: Optional[Dict[str, Any]] = None
    """
    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str,
        pool_mode: Optional[str] = None,
        *,
        ssl: str | bool = "require",
        statement_timeout_ms: int = 15000,
        connect_args: Optional[Dict[str, Any]] = None,
    ) -> None:
        # Build PostgreSQL URL using psycopg (v3) driver
        self.url = f"postgresql+psycopg://{user}:{password}@{host}:{port}/{database}"
        
        # Prepare connection arguments
        ca: Dict[str, Any] = {}
        
        # Handle SSL configuration
        if isinstance(ssl, bool):
            ca["sslmode"] = "require" if ssl else "disable"
        elif ssl == "disable":
            ca["sslmode"] = "disable"
        elif ssl in ["allow", "prefer", "require", "verify-ca", "verify-full"]:
            ca["sslmode"] = ssl
        else:
            ca["sslmode"] = "require"  # Default to secure
            
        # Add any additional connection arguments
        if connect_args:
            ca.update(connect_args)
        
        # Create engine with NullPool for PgBouncer compatibility
        self.engine: Engine = create_engine(
            self.url,
            poolclass=NullPool,  # Let PgBouncer handle pooling
            connect_args=ca,
            echo=False,  # Disable SQL logging
        )

    @contextmanager
    def get_connection(self):
        """Get a database connection context manager."""
        conn = self.engine.connect()
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def transaction(self):
        """Get a database connection with automatic transaction management."""
        conn = self.engine.connect()
        trans = conn.begin()
        try:
            yield conn
            trans.commit()
        except Exception:
            trans.rollback()
            raise
        finally:
            conn.close()

    def execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None):
        """Execute a query and return results."""
        with self.get_connection() as conn:
            if parameters:
                return conn.execute(text(query), parameters).fetchall()
            else:
                return conn.execute(text(query)).fetchall()

    def execute_one(self, query: str, parameters: Optional[Dict[str, Any]] = None):
        """Execute a query and return a single row."""
        with self.get_connection() as conn:
            if parameters:
                return conn.execute(text(query), parameters).fetchone()
            else:
                return conn.execute(text(query)).fetchone()

    def execute_scalar(self, query: str, parameters: Optional[Dict[str, Any]] = None):
        """Execute a query and return a single value."""
        with self.get_connection() as conn:
            if parameters:
                return conn.execute(text(query), parameters).scalar()
            else:
                return conn.execute(text(query)).scalar()

    def execute_command(self, command: str, parameters: Optional[Dict[str, Any]] = None):
        """Execute a command (INSERT, UPDATE, DELETE) and commit."""
        with self.get_connection() as conn:
            if parameters:
                result = conn.execute(text(command), parameters)
            else:
                result = conn.execute(text(command))
            conn.commit()
            return result.rowcount

    def test_connection(self) -> bool:
        """Test if the connection works."""
        try:
            result = self.execute_scalar("SELECT 1")
            return result == 1
        except Exception:
            return False

    def dispose(self) -> None:
        """Dispose of the engine."""
        if hasattr(self, 'engine'):
            self.engine.dispose()

    # Async compatibility methods using anyio.to_thread for proper non-blocking behavior
    async def async_execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None):
        """Async wrapper for execute_query - runs in thread pool to avoid blocking event loop."""
        import anyio
        return await anyio.to_thread.run_sync(self.execute_query, query, parameters)

    async def async_execute_one(self, query: str, parameters: Optional[Dict[str, Any]] = None):
        """Async wrapper for execute_one - runs in thread pool to avoid blocking event loop."""
        import anyio
        return await anyio.to_thread.run_sync(self.execute_one, query, parameters)

    async def async_execute_scalar(self, query: str, parameters: Optional[Dict[str, Any]] = None):
        """Async wrapper for execute_scalar - runs in thread pool to avoid blocking event loop."""
        import anyio
        return await anyio.to_thread.run_sync(self.execute_scalar, query, parameters)

    async def async_execute_command(self, command: str, parameters: Optional[Dict[str, Any]] = None):
        """Async wrapper for execute_command - runs in thread pool to avoid blocking event loop."""
        import anyio
        return await anyio.to_thread.run_sync(self.execute_command, command, parameters)

    async def async_test_connection(self) -> bool:
        """Async wrapper for test_connection - runs in thread pool to avoid blocking event loop."""
        import anyio
        return await anyio.to_thread.run_sync(self.test_connection)

    @asynccontextmanager
    async def async_transaction(self):
        """Async transaction wrapper - runs in thread pool to avoid blocking event loop."""
        import anyio
        
        async def _async_transaction():
            with self.transaction() as conn:
                yield conn
        
        async with anyio.to_thread.run_sync(_async_transaction) as conn:
            yield conn