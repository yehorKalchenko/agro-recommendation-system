"""
Database connection and session management.
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Create async engine
engine = None
AsyncSessionLocal = None


def get_database_url(async_driver: bool = True) -> str:
    """
    Build database URL from settings.

    Args:
        async_driver: If True, use asyncpg driver. If False, use psycopg2 for migrations.

    """
    if settings.DATABASE_URL:
        # Use full URL if provided, replace driver if needed
        url = settings.DATABASE_URL
        if not async_driver and "+asyncpg" in url:
            url = url.replace("+asyncpg", "+psycopg2")
        elif async_driver and "+psycopg2" in url:
            url = url.replace("+psycopg2", "+asyncpg")
        return url

    # Build from components
    user = settings.POSTGRES_USER or "postgres"
    password = settings.POSTGRES_PASSWORD or ""
    host = settings.POSTGRES_HOST or "localhost"
    port = settings.POSTGRES_PORT or 5432
    db = settings.POSTGRES_DB or "agrodiag"

    driver = "asyncpg" if async_driver else "psycopg2"

    if password:
        return f"postgresql+{driver}://{user}:{password}@{host}:{port}/{db}"
    else:
        return f"postgresql+{driver}://{user}@{host}:{port}/{db}"


def init_db():
    """Initialize database engine and session maker."""
    global engine, AsyncSessionLocal

    database_url = get_database_url()
    logger.info(f"Initializing database: {database_url.split('@')[-1]}")

    engine = create_async_engine(
        database_url,
        poolclass=NullPool,  # Disable connection pooling for async
        echo=settings.DB_ECHO,  # Log SQL queries if enabled
    )

    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    logger.info("Database initialized successfully")


async def get_db() -> AsyncSession:
    """
    Dependency for FastAPI endpoints to get DB session.

    Usage:
        @app.get("/endpoint")
        async def endpoint(db: AsyncSession = Depends(get_db)):
            ...
    """
    if AsyncSessionLocal is None:
        init_db()

    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables():
    """Create all database tables. Use only for development."""
    from app.db.models import Base

    if engine is None:
        init_db()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database tables created")


async def drop_tables():
    """Drop all database tables. Use with caution!"""
    from app.db.models import Base

    if engine is None:
        init_db()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    logger.info("Database tables dropped")
