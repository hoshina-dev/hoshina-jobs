"""Database connection and validation utilities."""
import psycopg
from psycopg import sql
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
    - hstore extension
    
    Raises:
        DatabaseError: If connection fails or required extensions missing
    """
    try:
        # Build connection string
        conn_str = (
            f"host={config.db_host} "
            f"port={config.db_port} "
            f"dbname={config.db_name} "
            f"user={config.db_user} "
            f"password={config.db_password}"
        )
        
        with psycopg.connect(conn_str) as conn:
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
                    raise DatabaseError(
                        f"Database must use UTF8 encoding, found: {encoding}"
                    )
                
                # Ensure PostGIS extension exists
                cur.execute("CREATE EXTENSION IF NOT EXISTS postgis")
                cur.execute("SELECT PostGIS_version()")
                postgis_version = cur.fetchone()[0].split()[0]
                
                # Ensure hstore extension exists
                cur.execute("CREATE EXTENSION IF NOT EXISTS hstore")
                
                conn.commit()
                
    except psycopg.OperationalError as e:
        raise DatabaseError(f"Failed to connect to database: {e}")
    except psycopg.Error as e:
        raise DatabaseError(f"Database error: {e}")


def check_existing_data(config: Config) -> bool:
    """Check if OSM data tables already exist.
    
    Note: osm2pgsql append mode has bugs, so this tool only supports
    one region per database. If tables exist, processing will be skipped.
    
    Returns:
        True if osm2pgsql tables exist (data already loaded)
        False if no tables (ready for initial import)
    """
    conn_str = (
        f"host={config.db_host} "
        f"port={config.db_port} "
        f"dbname={config.db_name} "
        f"user={config.db_user} "
        f"password={config.db_password}"
    )
    
    try:
        with psycopg.connect(conn_str) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT EXISTS ("
                    "  SELECT FROM information_schema.tables "
                    "  WHERE table_name IN ('planet_osm_point', 'planet_osm_line', 'planet_osm_polygon')"
                    ")"
                )
                return cur.fetchone()[0]
    except psycopg.Error as e:
        raise DatabaseError(f"Failed to check existing tables: {e}")
