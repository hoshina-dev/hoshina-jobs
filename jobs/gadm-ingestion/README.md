# GADM Ingestion Job

This job downloads the GADM administrative levels geopackage, uploads its contents to PostgreSQL/PostGIS, and keeps the compressed archive to avoid repeated downloads.

**Pipeline:** Download `gadm_410-levels.zip` → verify MD5 → extract `gadm_410-levels.gpkg` → upload to DB → remove `.gpkg` (keep `.zip`)

## Key behavior

- The pipeline stores an MD5 checksum file at `DATA_DIR/gadm_410-levels.md5`.
- The MD5 is calculated against the **.zip** archive (not the extracted `.gpkg` to save space).
- If the `.zip` exists and the MD5 matches, the job skips re-downloading and simply extracts the `.gpkg`.
- After a successful upload, the `cleanup_geopackage()` helper removes the extracted `.gpkg` to save disk space; the `.zip` is preserved for future runs.

## Files produced

- `gadm_410-levels.zip` — compressed archive (kept between runs)
- `gadm_410-levels.gpkg` — extracted geopackage (created for upload and removed afterwards)
- `gadm_410-levels.md5` — stored MD5 of the `.zip` archive

## Configuration

This job reads configuration via the project's config loader (see `src/config.py`). Important settings:

- `data_dir` — where downloaded files, `.gpkg`, and `.md5` are stored
- `gadm_geopackage_url` — the remote URL for the `gadm_410-levels.zip`

Set those values in your environment or config file as your project uses.

## Run locally

From the `jobs/gadm-ingestion` package you can run the ingestion with:

```bash
python -m src --force   # use --force to override existing DB checks
```

Typical flow run by the package's `__main__`:

1. `download_geopackage_levels(config)` — download (if needed) and extract `.gpkg`
2. `upload_levels_gpkg(config, force)` — upload extracted data to the database
3. `cleanup_geopackage(config)` — remove the `.gpkg`, keep the `.zip` and `.md5`

## Notes

- Keeping the `.zip` saves bandwidth and speeds reruns; MD5 ensures integrity.
- If you need to force a full re-download, remove the `gadm_410-levels.zip` or `gadm_410-levels.md5` in `data_dir`.
- The code intentionally computes MD5 on the `.zip` to minimize storage of large extracted files while still verifying content.
