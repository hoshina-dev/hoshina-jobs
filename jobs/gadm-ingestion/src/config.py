import os
from dataclasses import dataclass
from pathlib import Path

class ConfigurationError(Exception):
    """Raised when required configuration is missing or invalid."""


@dataclass
class Config:
    """Boundary data ingestion configuration loaded from environment variables."""
    # Database connection (REQUIRED for upload)
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str
    

    data_dir: Path
    ogr2ogr_path: str 
    
    # Download source
    gadm_geopackage_url: str
    
    @property
    def raw_dir(self) -> Path:
        """Directory for downloaded GADM geopackage file."""
        return self.data_dir / "gadm_410-levels.gpkg"
    
    @property
    def zip_dir(self) -> Path:
        """Directory for downloaded GADM geopackage zip file."""
        return self.data_dir / "gadm_410-levels.zip"
    
    @property
    def md5_dir(self) -> Path:
        """Directory for stored MD5 checksum file."""
        return self.data_dir / "gadm_410-levels.md5"
    
    
    def get_download_url(self) -> str:
        """Get the download URL for the configured region.
        
        Uses GEOFABRIK_BASE_URL if set, otherwise uses default.
        """
        return self.gadm_geopackage_url
    
    @property
    def connection_string(self) -> str:
        """PostgreSQL connection string."""
        return (
        f"host={self.db_host} "
        f"port={self.db_port} "
        f"dbname={self.db_name} "
        f"user={self.db_user} "
        f"password={self.db_password}"
    )

def get_env_bool(key: str, default: bool = False) -> bool:
    """Parse boolean from environment variable.
    
    Accepts: true/false, 1/0, yes/no (case-insensitive)
    """
    value = os.getenv(key, "").lower()
    if not value:
        return default
    return value in ("true", "1", "yes", "on")


def get_env_int(key: str, default: int) -> int:
    """Parse integer from environment variable."""
    value = os.getenv(key)
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        raise ConfigurationError(f"{key} must be an integer, got: {value}")

def load_config() -> Config:
    """Load and validate configuration from environment variables.
    
    Raises:
        ConfigurationError: If required configuration is missing or invalid.
    """
    # from dotenv import load_dotenv
    # load_dotenv() 
    db_host = os.getenv("DB_HOST", "").strip()
    db_name = os.getenv("DB_NAME", "").strip()
    db_user = os.getenv("DB_USER", "").strip()
    db_password = os.getenv("DB_PASSWORD", "").strip()
    
    if not db_host:
        raise ConfigurationError("DB_HOST environment variable is required")
    if not db_name:
        raise ConfigurationError("DB_NAME environment variable is required")
    if not db_user:
        raise ConfigurationError("DB_USER environment variable is required")
    if not db_password:
        raise ConfigurationError("DB_PASSWORD environment variable is required")
    
    db_port = get_env_int("DB_PORT", 5432)

    data_dir = Path(os.getenv("DATA_DIR", "/app/data"))
    ogr2ogr_path = os.getenv("OGR2OGR_PATH", "/usr/bin/ogr2ogr")
    
    gadm_geopackage_url = os.getenv("GADM_GEOPACKAGE_URL")
    if not gadm_geopackage_url:
        raise ConfigurationError("GADM_GEOPACKAGE_URL environment variable is required")

    
    return Config(
        db_host=db_host,
        db_port=db_port,
        db_name=db_name,
        db_user=db_user,
        db_password=db_password,
        data_dir=data_dir,
        ogr2ogr_path=ogr2ogr_path,
        gadm_geopackage_url=gadm_geopackage_url
    )

