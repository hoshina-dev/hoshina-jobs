from pathlib import Path
import hashlib
import zipfile
import requests
from .config import Config


def _read_md5(file_path: Path):
    """Read stored MD5 checksum from file."""
    md5_file = file_path
    if md5_file.exists():
        return md5_file.read_text().strip()
    return None


def _write_md5(md5_hash: str, file_path: Path):
    """Write MD5 checksum to file."""
    md5_file = file_path
    md5_file.parent.mkdir(parents=True, exist_ok=True)
    md5_file.write_text(md5_hash)


def _calculate_md5(file_path: Path) -> str:
    """Calculate MD5 checksum of a file."""
    md5_hash = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()


def download_geopackage_levels(config: Config) -> Path:
    """Download and extract gadm_410-levels.gpkg with MD5 verification on .zip.
    
    - Skips download if .zip exists with correct MD5
    - Downloads .zip from GADM servers if needed
    - Extracts .gpkg from .zip
    - Keeps .zip for future use (avoids re-downloading)
    """
    data_dir = config.data_dir
    data_dir.mkdir(parents=True, exist_ok=True)
    
    gpkg_file = config.raw_dir
    zip_file = config.zip_dir
    stored_md5 = _read_md5(file_path=config.md5_dir)
    
    if not zip_file.exists() or not stored_md5 or _calculate_md5(zip_file) != stored_md5:
        print("Downloading gadm_410-levels.zip...")
        try:
            response = requests.get(config.gadm_geopackage_url, stream=True, timeout=6000)
            response.raise_for_status()
            with open(zip_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        except requests.Timeout:
            print(f"✗ Download timeout (exceeded 100 minutes), something is wrong. The file size is only 2 GB.")
            raise
        except requests.RequestException as e:
            print(f"✗ Failed: {e}")
            raise
        
        print("✓ Download completed")
        new_md5 = _calculate_md5(zip_file)
        _write_md5(new_md5, file_path=config.md5_dir)
    else:
        print(f"✓ .zip exists with correct checksum, skipping download")
    
    _extract_gpkg(zip_file, gpkg_file)
    
    print(f"✓ gadm_410-levels.gpkg ready")
    return gpkg_file


def _extract_gpkg(zip_file: Path, gpkg_file: Path) -> None:
    """Extract .gpkg from .zip file."""
    try:
        print(f"Extracting {zip_file}")
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            for file_info in zip_ref.filelist:
                if file_info.filename.endswith('.gpkg'):
                    zip_ref.extract(file_info, zip_file.parent)
                    extracted_file = zip_file.parent / file_info.filename
                    if extracted_file != gpkg_file:
                        extracted_file.rename(gpkg_file)
                    break
        print(f"✓ Extracted: {gpkg_file}")
    except Exception as e:
        print(f"✗ Failed: {e}")
        raise


def cleanup_geopackage(config: Config) -> None:
    """Delete .gpkg file after upload, keeping .zip for future use.
    
    Call this function after upload.py completes successfully.
    """
    gpkg_file = config.raw_dir
    
    if gpkg_file.exists():
        gpkg_file.unlink()
        print(f"✓ Cleaned up {gpkg_file}")
    else:
        print(f"X {gpkg_file} not found, nothing to clean")