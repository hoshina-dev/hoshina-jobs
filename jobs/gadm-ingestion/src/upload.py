from .config import Config
import sqlite3
import psycopg
from psycopg import sql
import subprocess
import os

def upload_levels_gpkg(config: Config) -> None:
    """Upload GADM data from gadm_410-levels.gpkg (already separated by admin level).
    
    Args:
        config (Config): Configuration with database connection info.
    """
    gpkg_path = config.raw_dir
    if not gpkg_path.exists():
        raise FileNotFoundError(f"GeoPackage not found: {gpkg_path}")
    
    conn_sqlite = sqlite3.connect(str(gpkg_path))
    cur_sqlite = conn_sqlite.cursor()
    cur_sqlite.execute("SELECT table_name FROM gpkg_contents WHERE data_type = 'features' ORDER BY table_name")
    layers = [row[0] for row in cur_sqlite.fetchall()]
    conn_sqlite.close()
    
    if not layers:
        raise ValueError(f"No feature layers found in {gpkg_path}")
    
    print(f"Found {len(layers)} layers: {', '.join(layers)}")
    
    with psycopg.connect(config.connection_string) as conn:
        for layer in layers:
            parts = layer.split('_')
            if len(parts) < 2:
                raise ValueError(f"Invalid layer name format: {layer}. Expected format: gadmN_admN")
            level = parts[1]
            table_name = f"admin{level}"
            print(f"Importing {layer} → {table_name}...", end="", flush=True)

            env = os.environ.copy()
            cmd = [
                config.ogr2ogr_path,
                "--config" ,"PG_USE_COPY", "YES",
                "-overwrite",
                "-gt", "100000",
                "-f", "PostgreSQL",
                "-nln", table_name,
                "-nlt", "PROMOTE_TO_MULTI",
                "-lco", "GEOMETRY_NAME=geom",
                "-lco", "FID=ogc_fid",
                "-lco", "SPATIAL_INDEX=GIST",
                "-sql", f"SELECT * FROM {layer}",
                f"PG:{config.connection_string}"
            ]
                
            cmd.append(str(gpkg_path))
            
            subprocess.run(cmd, check=True, capture_output=True, text=True, env=env)
      
            with conn.cursor() as cur:
                cur.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(table_name)))
                result = cur.fetchone()
                count = result[0] if result else 0
            
            conn.commit()
            print(f" ✓ {count:,} rows")
        
        print("\n✓ Upload complete!")