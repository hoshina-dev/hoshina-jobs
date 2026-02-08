"""Allow running as python -m src"""
import sys
from .download import download_geopackage_levels, cleanup_geopackage
from .config import load_config, ConfigurationError
from .database import verify_connection, check_existing_data
from .upload import upload_levels_gpkg
import argparse


def main(force: bool = False) -> int:
    try:
        config = load_config()
    except ConfigurationError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        return 1
    
    verify_connection(config) 
    
    if check_existing_data(config) and not force:
        print("Existing GADM data found in the database. Skipping download to avoid overwriting or use --force to override.", file=sys.stderr)
        return 0
    
    download_geopackage_levels(config)
    upload_levels_gpkg(config)
    cleanup_geopackage(config)
    return 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GADM Data Ingestion")
    parser.add_argument('--force', action='store_true', help='Force re-download and upload of GADM data')
    args = parser.parse_args()
    sys.exit(main(force=args.force))
    
