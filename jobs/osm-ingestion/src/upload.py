"""Upload OSM data to PostgreSQL database using osm2pgsql."""
import os
import re
import subprocess
import time
from pathlib import Path

from .config import Config


class UploadError(Exception):
    """Raised when upload/import fails."""
    pass


def upload_to_database(config: Config, pbf_file: Path) -> None:
    """Upload filtered OSM data to PostgreSQL using osm2pgsql.
    
    Uses --create mode (append not supported due to osm2pgsql bugs).
    Shows progress updates for visibility.
    
    Args:
        config: Configuration object with database settings
        pbf_file: Path to filtered .osm.pbf file
        
    Raises:
        UploadError: If upload fails
    """
    print(f"Importing {pbf_file.name} to database...")
    print(f"Database: {config.db_host}:{config.db_port}/{config.db_name}")
    print(f"Cache size: {config.cache_size_mb} MB")
    print(f"Processes: {config.num_processes}")
    
    # Build osm2pgsql command
    cmd = [
        "osm2pgsql",
        "--slim",                    # Use slim mode for large datasets
        "--hstore",                  # Store all tags in hstore column
        "--multi-geometry",          # Handle multi-geometries properly
        "--create",                  # Create mode (not append - it's buggy)
        "-d", config.db_name,
        "-U", config.db_user,
        "-H", config.db_host,
        "-P", str(config.db_port),
        "-S", "/usr/share/osm2pgsql/default.style",  # Standard style file
        "--cache", str(config.cache_size_mb),
        "--number-processes", str(config.num_processes),
    ]
    
    # Add drop flag if configured (saves space but prevents updates)
    if config.drop_slim_tables:
        cmd.append("--drop")
        print("⚠ Using --drop flag - slim tables will be removed (updates disabled)")
    
    # Add input file
    cmd.append(str(pbf_file))
    
    # Prepare environment with password
    env = os.environ.copy()
    env["PGPASSWORD"] = config.db_password
    
    try:
        # Run with real-time output streaming
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env
        )
        
        start_time = time.time()
        processing_phase = "Reading"
        
        # Stream output and parse progress
        for line in process.stdout:
            line = line.strip()
            if not line:
                continue
            
            # Parse osm2pgsql output for progress and phases
            # Common patterns:
            # "Processing: Node(123456k 45.6k/s) Way(0k 0.00k/s)"
            # "Node stats: total(12345678), max(12345678)"
            # "Reading in file: /path/to/file.osm.pbf"
            # "Processing: Way(123456k 12.3k/s)"
            # "Going over pending ways (using 8 threads)"
            
            # Detect processing phases
            if "Reading in file:" in line:
                processing_phase = "Reading"
                print(f"Phase: Reading file...")
            elif "Processing: Node" in line or "Node(" in line:
                if processing_phase != "Nodes":
                    processing_phase = "Nodes"
                    print(f"Phase: Processing nodes...")
            elif "Processing: Way" in line or "Going over pending ways" in line:
                if processing_phase != "Ways":
                    processing_phase = "Ways"
                    print(f"Phase: Processing ways...")
            elif "Processing: Relation" in line:
                if processing_phase != "Relations":
                    processing_phase = "Relations"
                    print(f"Phase: Processing relations...")
            elif "Clustering" in line or "Creating indexes" in line:
                if processing_phase != "Indexing":
                    processing_phase = "Indexing"
                    print(f"Phase: Creating indexes...")
            
            # Parse progress numbers
            # Format: "Node(123456k 45.6k/s)" or "Way(123456k 12.3k/s)"
            progress_match = re.search(r'(Node|Way|Relation)\((\d+\.?\d*)k\s+(\d+\.?\d*)k/s\)', line)
            if progress_match:
                obj_type = progress_match.group(1)
                count = progress_match.group(2)
                rate = progress_match.group(3)
                elapsed = time.time() - start_time
                print(f"  {obj_type}s: {count}k processed - {rate}k/s - {elapsed:.1f}s elapsed")
            
            # Show stats when completed
            elif "stats: total" in line.lower():
                print(f"  ✓ {line}")
            
            # Show warnings/errors
            elif "WARNING" in line.upper() or "ERROR" in line.upper():
                print(f"  ⚠ {line}")
        
        # Wait for completion
        return_code = process.wait()
        
        if return_code != 0:
            raise UploadError(f"osm2pgsql failed with exit code {return_code}")
        
        elapsed = time.time() - start_time
        print(f"✓ Import completed in {elapsed:.1f}s ({elapsed/60:.1f} minutes)")
        
    except FileNotFoundError:
        raise UploadError(
            "osm2pgsql command not found. Ensure osm2pgsql is installed in the container."
        )
    except Exception as e:
        raise UploadError(f"Upload operation failed: {e}")
