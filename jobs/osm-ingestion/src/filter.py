"""Filter OSM data to extract specific features."""
import subprocess
from pathlib import Path
from typing import List

from .config import Config


class FilterError(Exception):
    """Raised when filtering fails."""
    pass


def filter_roads(input_file: Path, output_file: Path) -> None:
    """Filter OSM file to include only roads.
    
    Uses osmium tags-filter to extract ways with highway tag.
    Shows progress updates for better visibility.
    
    Args:
        input_file: Path to input .osm.pbf file
        output_file: Path to output filtered .osm.pbf file
        
    Raises:
        FilterError: If filtering fails
    """
    print(f"Filtering roads from {input_file.name}...")
    
    # Ensure output directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Build osmium command for road filtering
    # w/highway = ways with highway tag (all road types)
    cmd = [
        "osmium",
        "tags-filter",
        str(input_file),
        "w/highway",  # Filter: ways with highway tag
        "-o", str(output_file),
        "--overwrite",
        "--progress"  # Show progress for visibility
    ]
    
    try:
        # Run with real-time output streaming
        import re
        import time
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        last_reported_percent = -1
        start_time = time.time()
        
        # Stream output and parse progress
        for line in process.stdout:
            line = line.strip()
            if not line:
                continue
            
            # osmium progress format examples:
            # "[===>    ] 45% 1234567/2345678"
            # "[========] 100%"
            # Parse percentage and counts for detailed updates
            if '%' in line:
                try:
                    # Extract percentage
                    percent_match = re.search(r'(\d+)%', line)
                    if percent_match:
                        percent = int(percent_match.group(1))
                        
                        # Extract counts if available (format: current/total)
                        count_match = re.search(r'(\d+)/(\d+)', line)
                        
                        # Report every 10% for cleaner logs
                        if percent >= last_reported_percent + 10:
                            elapsed = time.time() - start_time
                            
                            if count_match:
                                current = int(count_match.group(1))
                                total = int(count_match.group(2))
                                
                                # Calculate rate
                                rate = current / elapsed if elapsed > 0 else 0
                                
                                # Format counts nicely
                                current_str = f"{current:,}"
                                total_str = f"{total:,}"
                                rate_str = f"{int(rate):,}"
                                
                                print(f"Filter progress: {percent}% ({current_str}/{total_str} objects) - {rate_str} obj/s - {elapsed:.1f}s elapsed")
                            else:
                                print(f"Filter progress: {percent}% - {elapsed:.1f}s elapsed")
                            
                            last_reported_percent = percent
                except (ValueError, IndexError, AttributeError):
                    # If parsing fails, show minimal progress
                    if last_reported_percent < 0:
                        print(f"Filtering in progress...")
                        last_reported_percent = 0
        
        # Wait for completion
        return_code = process.wait()
        
        if return_code != 0:
            raise FilterError(f"osmium tags-filter failed with exit code {return_code}")
        
        elapsed = time.time() - start_time
        print(f"Filter progress: 100% - completed in {elapsed:.1f}s")
        
        # Get file sizes
        input_size = input_file.stat().st_size / (1024**3)
        output_size = output_file.stat().st_size / (1024**3)
        reduction = ((input_size - output_size) / input_size * 100) if input_size > 0 else 0
        
        print(f"Input size: {input_size:.2f} GB")
        print(f"Output size: {output_size:.2f} GB")
        print(f"Size reduction: {reduction:.1f}%")
        
    except FileNotFoundError:
        raise FilterError(
            "osmium command not found. Ensure osmium-tool is installed in the container."
        )
    except Exception as e:
        raise FilterError(f"Filter operation failed: {e}")


# TODO: Future enhancement - support filtering other OSM features
# Possible filters to add:
#
# def filter_buildings(input_file: Path, output_file: Path) -> None:
#     """Filter buildings: w/building"""
#     pass
#
# def filter_waterways(input_file: Path, output_file: Path) -> None:
#     """Filter waterways: w/waterway"""
#     pass
#
# def filter_railways(input_file: Path, output_file: Path) -> None:
#     """Filter railways: w/railway"""
#     pass
#
# def filter_landuse(input_file: Path, output_file: Path) -> None:
#     """Filter landuse: w/landuse,a/landuse"""
#     pass
#
# def filter_custom(input_file: Path, output_file: Path, tags: List[str]) -> None:
#     """Filter with custom tag filters.
#     
#     Example tags:
#     - 'w/highway' - ways with highway tag
#     - 'w/building' - ways with building tag
#     - 'n/amenity' - nodes with amenity tag
#     - 'a/landuse' - areas with landuse tag
#     - 'r/route=bus' - relations with route=bus
#     """
#     cmd = ["osmium", "tags-filter", str(input_file)] + tags + ["-o", str(output_file)]
#     # ... implementation
#     pass


def filter_osm_data(config: Config, input_file: Path) -> Path:
    """Filter OSM data based on configuration.
    
    Currently only supports road filtering.
    Future: Could support config.feature_type to filter different features.
    
    Args:
        config: Configuration object
        input_file: Path to raw OSM file
        
    Returns:
        Path to filtered output file
        
    Raises:
        FilterError: If filtering fails
    """
    # Generate output filename
    base_name = input_file.stem.replace("-latest", "")
    output_file = config.filtered_dir / f"{base_name}-roads.osm.pbf"
    
    # Check if already filtered
    if output_file.exists():
        output_size = output_file.stat().st_size / (1024**3)
        print(f"Filtered file already exists: {output_file.name} ({output_size:.2f} GB)")
        print("Skipping filter step")
        return output_file
    
    # Currently only roads are supported
    # TODO: Add config.feature_type to support other filters
    filter_roads(input_file, output_file)
    
    return output_file
