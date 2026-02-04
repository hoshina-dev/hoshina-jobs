"""OSM Ingestion - Main entry point."""
import sys
from .config import load_config, ConfigurationError
from .database import verify_connection, check_existing_data, DatabaseError
from .download import download_region, DownloadError
from .filter import filter_osm_data, FilterError
from .upload import upload_to_database, UploadError


def main() -> int:
    """Main entry point for OSM ingestion pipeline.
    
    Returns:
        Exit code: 0 for success, non-zero for failure
    """
    # Step 1: Load configuration
    try:
        config = load_config()
    except ConfigurationError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        return 1
    
    print(f"Loaded configuration for region: {config.region}")
    print(f"Database: {config.db_host}:{config.db_port}/{config.db_name}")
    
    # Step 2: Verify database connection
    try:
        print("Verifying database connection...")
        verify_connection(config)
        print("✓ Database connection verified")
        print("✓ PostGIS extension available")
        print("✓ hstore extension available")
    except DatabaseError as e:
        print(f"Database error: {e}", file=sys.stderr)
        return 4
    
    # Step 3: Check for existing data
    # Note: osm2pgsql append mode has bugs, so we only support one region per database
    try:
        if check_existing_data(config):
            print("✓ OSM tables already exist in database")
            print("⚠ Cannot append data - osm2pgsql append mode is not supported")
            print("  To process a different region, use a separate database")
            print("Pipeline complete (skipping - data already present)")
            return 0
    except DatabaseError as e:
        print(f"Database error: {e}", file=sys.stderr)
        return 4
    
    # Step 4: Download OSM data
    print("\n--- Step 1: Download ---")
    try:
        raw_file = download_region(config)
        print(f"✓ Raw file ready: {raw_file.name}\n")
    except DownloadError as e:
        print(f"Download error: {e}", file=sys.stderr)
        return 2
    
    # Step 5: Filter roads
    print("--- Step 2: Filter ---")
    try:
        filtered_file = filter_osm_data(config, raw_file)
        print(f"✓ Filtered file ready: {filtered_file.name}\n")
    except FilterError as e:
        print(f"Filter error: {e}", file=sys.stderr)
        return 3
    
    # Cleanup raw file if configured
    if config.cleanup and raw_file.exists():
        print(f"Cleaning up raw file: {raw_file.name}")
        raw_file.unlink()
        print("✓ Raw file deleted\n")
    
    # Step 6: Upload to database
    print("--- Step 3: Upload ---")
    try:
        upload_to_database(config, filtered_file)
        print(f"✓ Data imported to database\n")
    except UploadError as e:
        print(f"Upload error: {e}", file=sys.stderr)
        return 4
    
    # Cleanup filtered file if configured
    if config.cleanup and filtered_file.exists():
        print(f"Cleaning up filtered file: {filtered_file.name}")
        filtered_file.unlink()
        print("✓ Filtered file deleted\n")
    
    print("=" * 60)
    print("Pipeline complete!")
    print(f"Region: {config.region}")
    print(f"Database: {config.db_host}:{config.db_port}/{config.db_name}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
