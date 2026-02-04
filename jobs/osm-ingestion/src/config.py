import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


class ConfigurationError(Exception):
    """Raised when required configuration is missing or invalid."""
    pass


@dataclass
class Config:
    """OSM ingestion configuration loaded from environment variables."""
    
    # Region selection (REQUIRED)
    region: str
    
    # Database connection (REQUIRED for upload)
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str
    
    # Processing options
    cache_size_mb: int
    num_processes: int
    cleanup: bool
    drop_slim_tables: bool
    
    # Storage
    data_dir: Path
    
    # Download source
    geofabrik_base_url: str
    
    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"]
    log_format: Literal["json", "text"]
    
    @property
    def raw_dir(self) -> Path:
        """Directory for raw downloaded OSM files."""
        return self.data_dir / "raw"
    
    @property
    def filtered_dir(self) -> Path:
        """Directory for filtered OSM files (roads only)."""
        return self.data_dir / "filtered"
    
    def get_download_url(self) -> str:
        """Get the download URL for the configured region.
        
        Uses GEOFABRIK_BASE_URL if set, otherwise uses default.
        """
        # Special handling for planet - different base URL
        if self.region == "planet":
            if "download.geofabrik.de" in self.geofabrik_base_url:
                return "https://planet.openstreetmap.org/pbf/planet-latest.osm.pbf"
            else:
                # For local cache, use same base URL
                return f"{self.geofabrik_base_url}/planet-latest.osm.pbf"
        
        # Standard regions
        return f"{self.geofabrik_base_url}/{self.region}-latest.osm.pbf"


# Supported OSM regions
REGIONS = [
    "africa",
    "antarctica",
    "asia",
    "australia-oceania",
    "central-america",
    "europe",
    "north-america",
    "south-america",
    "planet"
]


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
    # Load region (REQUIRED)
    region = os.getenv("OSM_REGION", "").strip()
    if not region:
        raise ConfigurationError(
            "OSM_REGION environment variable is required.\n"
            f"Available regions: {', '.join(REGIONS)}"
        )
    
    if region not in REGIONS:
        raise ConfigurationError(
            f"Invalid region: {region}\n"
            f"Available regions: {', '.join(REGIONS)}"
        )
    
    # Load database configuration (REQUIRED)
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
    
    # Load processing options (with defaults)
    cache_size_mb = get_env_int("CACHE_SIZE_MB", 2000)
    num_processes = get_env_int("NUM_PROCESSES", 4)
    cleanup = get_env_bool("CLEANUP", True)
    drop_slim_tables = get_env_bool("DROP_SLIM_TABLES", False)
    
    # Load storage configuration
    data_dir = Path(os.getenv("DATA_DIR", "/app/data"))
    
    # Load download source configuration
    geofabrik_base_url = os.getenv("GEOFABRIK_BASE_URL", "https://download.geofabrik.de").rstrip("/")
    
    # Load logging configuration
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    if log_level not in ("DEBUG", "INFO", "WARNING", "ERROR"):
        raise ConfigurationError(
            f"Invalid LOG_LEVEL: {log_level}. "
            "Must be one of: DEBUG, INFO, WARNING, ERROR"
        )
    
    log_format = os.getenv("LOG_FORMAT", "json").lower()
    if log_format not in ("json", "text"):
        raise ConfigurationError(
            f"Invalid LOG_FORMAT: {log_format}. Must be 'json' or 'text'"
        )
    
    return Config(
        region=region,
        db_host=db_host,
        db_port=db_port,
        db_name=db_name,
        db_user=db_user,
        db_password=db_password,
        cache_size_mb=cache_size_mb,
        num_processes=num_processes,
        cleanup=cleanup,
        drop_slim_tables=drop_slim_tables,
        data_dir=data_dir,
        geofabrik_base_url=geofabrik_base_url,
        log_level=log_level,  # type: ignore
        log_format=log_format,  # type: ignore
    )
