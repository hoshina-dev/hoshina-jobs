"""Database connection and validation utilities."""
import psycopg
from .config import Config


class DatabaseError(Exception):
    """Raised when database operations fail."""
    pass


def verify_connection(config: Config) -> None:
    """Verify database connection and required extensions.
    
    Checks:
    - Connection to PostgreSQL
    - UTF8 encoding
    - PostGIS extension
    
    Raises:
        DatabaseError: If connection fails or required extensions missing
    """
    try:
        with psycopg.connect(config.connection_string) as conn:
            with conn.cursor() as cur:
                # Check database encoding
                cur.execute(
                    "SELECT pg_encoding_to_char(encoding) FROM pg_database WHERE datname = %s",
                    (config.db_name,)
                )
                result = cur.fetchone()
                if not result:
                    raise DatabaseError(f"Database '{config.db_name}' not found")
                
                encoding = result[0]
                if encoding != "UTF8":
                    cur.execute("update pg_database set encoding = pg_char_to_encoding('UTF8') where datname = %s;", (config.db_name,))
                
                # Ensure PostGIS extension exists
                cur.execute("CREATE EXTENSION IF NOT EXISTS postgis")
                cur.execute("SELECT PostGIS_version()")
                
                # Ensure hstore extension exists
                cur.execute("CREATE EXTENSION IF NOT EXISTS hstore")
                
                conn.commit()
                
    except psycopg.OperationalError as e:
        raise DatabaseError(f"Failed to connect to database: {e}")
    except psycopg.Error as e:
        raise DatabaseError(f"Database error: {e}")


def check_existing_data(config: Config) -> bool:
    """Check if GADM data tables already exist.
    If tables exist, processing will be skipped.
    
    Returns:
        True if admin tables exist (data already loaded)
        False if no tables (ready for initial import)
    """
    try:
        with psycopg.connect(config.connection_string) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT EXISTS ("
                    "  SELECT FROM information_schema.tables "
                    "  WHERE table_name IN ('admin0', 'admin1', 'admin2', 'admin3', 'admin4', 'admin5')"
                    ")"
                )
                result = cur.fetchone()
                if result:
                    return result[0]
                return False
    except psycopg.Error as e:
        raise DatabaseError(f"Failed to check existing tables: {e}")
