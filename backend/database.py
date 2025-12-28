from sqlalchemy import create_engine, event, exc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool, QueuePool
import os
import logging
from dotenv import load_dotenv
from urllib.parse import urlparse

# Configure logging
logger = logging.getLogger(__name__)

load_dotenv()


class DatabaseConfigError(Exception):
    """Custom exception for database configuration errors"""
    pass


def _validate_database_url(database_url: str) -> str:
    """Validate database URL for security and correctness.
    
    Args:
        database_url: The database connection URL
        
    Returns:
        Validated database URL
        
    Raises:
        DatabaseConfigError: If URL is invalid or uses insecure defaults
    """
    if not database_url:
        raise DatabaseConfigError(
            "DATABASE_URL environment variable is not set. "
            "Please configure it with a valid database connection string."
        )
    
    # Check for default credentials (security risk) - only in production
    # In development/Docker, allow the test credentials
    is_production = os.getenv("ENVIRONMENT") == "production"
    
    if is_production:
        if "password@localhost" in database_url or "postgres:password" in database_url:
            raise DatabaseConfigError(
                "DATABASE_URL contains default credentials. "
                "Please update with actual credentials from environment variables."
            )
    else:
        # In development, just warn about default credentials
        if "postgres:password" in database_url:
            logger.warning(
                "DATABASE_URL contains test credentials. "
                "For production, use strong credentials."
            )
    
    # Parse and validate URL structure
    try:
        parsed = urlparse(database_url)
    except Exception as e:
        raise DatabaseConfigError(f"Invalid DATABASE_URL format: {str(e)}")
    
    # Validate scheme
    valid_schemes = {'postgresql', 'postgres', 'mysql', 'sqlite', 'oracle', 'mssql'}
    if parsed.scheme not in valid_schemes:
        raise DatabaseConfigError(
            f"Unsupported database scheme: {parsed.scheme}. "
            f"Supported: {valid_schemes}"
        )
    
    # Validate host for non-sqlite databases
    if parsed.scheme != 'sqlite' and not parsed.netloc:
        raise DatabaseConfigError(
            "DATABASE_URL missing hostname. Format should be: "
            "postgresql://user:password@host:port/database"
        )
    
    # Warn about missing credentials in production
    if parsed.scheme in {'postgresql', 'postgres', 'mysql'} and not parsed.password:
        logger.warning(
            "DATABASE_URL does not contain a password. "
            "This may indicate a configuration issue."
        )
    
    return database_url


def _get_database_url() -> str:
    """Get and validate database URL from environment.
    
    Returns:
        Validated database URL
        
    Raises:
        DatabaseConfigError: If DATABASE_URL is not configured properly
    """
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        raise DatabaseConfigError(
            "DATABASE_URL environment variable is required. "
            "Please set it in your .env file or environment."
        )
    
    return _validate_database_url(database_url)


# Initialize database URL with validation
try:
    DATABASE_URL = _get_database_url()
    logger.info("Database URL loaded successfully (credentials hidden)")
except DatabaseConfigError as e:
    logger.error(f"Database configuration error: {str(e)}")
    raise

# Optimize connection pool for better performance
try:
    # Determine connection pool settings based on database type
    parsed_url = urlparse(DATABASE_URL)
    is_sqlite = parsed_url.scheme == 'sqlite'
    
    # SQLite doesn't benefit from connection pooling
    pool_class = NullPool if is_sqlite else QueuePool
    
    engine = create_engine(
        DATABASE_URL,
        poolclass=pool_class,
        pool_size=10 if not is_sqlite else None,  # Connection pool size
        max_overflow=20 if not is_sqlite else None,  # Max overflow connections
        pool_pre_ping=True if not is_sqlite else False,  # Test connections before using
        pool_recycle=3600 if not is_sqlite else None,  # Recycle connections after 1 hour
        echo=False,  # Disable SQL logging for performance
        connect_args={"connect_timeout": 10} if not is_sqlite else {},  # Connection timeout
    )
    
    logger.info(f"Database engine created successfully (pool_class: {pool_class.__name__})")

except Exception as e:
    logger.error(f"Failed to create database engine: {str(e)}")
    raise DatabaseConfigError(f"Database engine initialization failed: {str(e)}")


# Event listener for connection pool errors
@event.listens_for(engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    """Handle new database connections"""
    try:
        logger.debug("New database connection established")
    except Exception as e:
        logger.warning(f"Error handling connection: {str(e)}")


@event.listens_for(engine, "close")
def receive_close(dbapi_conn, connection_record):
    """Handle database connection closure"""
    try:
        logger.debug("Database connection closed")
    except Exception as e:
        logger.warning(f"Error handling connection close: {str(e)}")


@event.listens_for(engine, "engine_disposed")
def receive_engine_disposed(engine):
    """Handle engine disposal"""
    logger.warning("Database engine disposed - pool connections recycled")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def _verify_database_connection() -> bool:
    """Verify that database connection is working.
    
    Returns:
        True if connection is successful
        
    Raises:
        DatabaseConfigError: If connection fails
    """
    try:
        with engine.connect() as connection:
            # Execute a simple query to verify connection
            connection.execute("SELECT 1")
            logger.info("Database connection verified successfully")
            return True
    
    except exc.OperationalError as e:
        logger.error(f"Database operational error: {str(e)}")
        raise DatabaseConfigError(
            f"Unable to connect to database. Please check your DATABASE_URL configuration: {str(e)}"
        )
    
    except exc.ArgumentError as e:
        logger.error(f"Database argument error: {str(e)}")
        raise DatabaseConfigError(
            f"Invalid database configuration: {str(e)}"
        )
    
    except Exception as e:
        logger.error(f"Unexpected database error: {str(e)}")
        raise DatabaseConfigError(
            f"Database connection failed: {str(e)}"
        )


def get_db():
    """Get database session with error handling.
    
    Yields:
        SQLAlchemy database session
        
    Raises:
        DatabaseConfigError: If database operations fail
    """
    db = SessionLocal()
    try:
        yield db
    
    except exc.SQLAlchemyError as e:
        logger.error(f"Database error during session: {str(e)}")
        db.rollback()
        raise
    
    except Exception as e:
        logger.error(f"Unexpected error during database session: {str(e)}")
        db.rollback()
        raise
    
    finally:
        db.close()
        logger.debug("Database session closed")


# Verify database connection on startup
try:
    _verify_database_connection()
except DatabaseConfigError as e:
    logger.critical(f"Critical database configuration error: {str(e)}")
    raise