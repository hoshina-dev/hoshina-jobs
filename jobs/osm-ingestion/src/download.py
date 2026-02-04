"""Download OSM data from GeoFabrik or custom mirror."""
import time
from pathlib import Path
from typing import Optional

import requests

from .config import Config


class DownloadError(Exception):
    """Raised when download fails."""
    pass


def format_size(bytes_size: int) -> str:
    """Format bytes to human-readable size.
    
    Args:
        bytes_size: Size in bytes
        
    Returns:
        Human-readable size string (e.g., "1.23 GB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} PB"


def download_region(config: Config) -> Path:
    """Download OSM data for the configured region.
    
    Downloads with periodic progress updates every 5% or 100MB.
    Log-friendly output for Kubernetes.
    
    Args:
        config: Configuration object
        
    Returns:
        Path to downloaded file
        
    Raises:
        DownloadError: If download fails
    """
    url = config.get_download_url()
    output_file = config.raw_dir / f"{config.region}-latest.osm.pbf"
    
    # Create directory if needed
    config.raw_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if file already exists
    if output_file.exists():
        file_size = output_file.stat().st_size
        print(f"File already exists: {output_file.name} ({format_size(file_size)})")
        print("Skipping download")
        return output_file
    
    print(f"Downloading: {config.region}")
    print(f"Source: {url}")
    print(f"Destination: {output_file}")
    
    try:
        # Start download with streaming
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        # Get total file size
        total_size = int(response.headers.get('content-length', 0))
        if total_size == 0:
            print("Warning: Unable to determine file size")
        else:
            print(f"File size: {format_size(total_size)}")
        
        # Download with progress tracking
        downloaded = 0
        last_reported_percent = -1
        last_reported_mb = -100  # Report every 100MB
        start_time = time.time()
        
        with open(output_file, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    # Report progress every 5% or every 100MB
                    if total_size > 0:
                        percent = int((downloaded / total_size) * 100)
                        if percent >= last_reported_percent + 5:
                            elapsed = time.time() - start_time
                            speed = downloaded / elapsed if elapsed > 0 else 0
                            print(f"Progress: {percent}% ({format_size(downloaded)} / {format_size(total_size)}) - {format_size(int(speed))}/s")
                            last_reported_percent = percent
                    else:
                        # If size unknown, report every 100MB
                        mb_downloaded = downloaded // (1024 * 1024)
                        if mb_downloaded >= last_reported_mb + 100:
                            elapsed = time.time() - start_time
                            speed = downloaded / elapsed if elapsed > 0 else 0
                            print(f"Progress: {format_size(downloaded)} downloaded - {format_size(int(speed))}/s")
                            last_reported_mb = mb_downloaded
        
        # Final report
        elapsed = time.time() - start_time
        avg_speed = downloaded / elapsed if elapsed > 0 else 0
        print(f"Download complete: {format_size(downloaded)} in {elapsed:.1f}s")
        print(f"Average speed: {format_size(int(avg_speed))}/s")
        
        return output_file
        
    except requests.exceptions.RequestException as e:
        # Clean up partial download
        if output_file.exists():
            output_file.unlink()
        raise DownloadError(f"Download failed: {e}")
    except Exception as e:
        # Clean up partial download
        if output_file.exists():
            output_file.unlink()
        raise DownloadError(f"Unexpected error during download: {e}")
