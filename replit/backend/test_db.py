from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

URL = "postgresql+psycopg://postgres.fpluepeqdswjacfaznky:aQI3TzR7k2yq0NG6@aws-1-ca-central-1.pooler.supabase.com:6543/postgres"

engine = create_engine(
    URL,
    poolclass=NullPool,                # let PgBouncer pool
    connect_args={"sslmode": "require"}  # libpq handles TLS
)

with engine.connect() as c:
    print(c.execute(text("SELECT now()")).scalar())