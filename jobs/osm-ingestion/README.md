# OSM Ingestion Job

Containerized job for ingesting OpenStreetMap road data into PostgreSQL with PostGIS. Part of the Hoshina jobs monorepo.

**Pipeline:** Download OSM data from GeoFabrik → Filter roads → Import to PostgreSQL

**Limitation:** One region per database (osm2pgsql append mode is buggy). Use separate databases for multiple regions.


## Configuration

### Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `OSM_REGION` | Region to process | `europe`, `asia`, `planet` |
| `DB_HOST` | PostgreSQL host | `postgres.default.svc.cluster.local` |
| `DB_NAME` | Database name | `osm_db` |
| `DB_USER` | Database user | `postgres` |
| `DB_PASSWORD` | Database password | `your_secure_password` |

### Optional Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_PORT` | `5432` | PostgreSQL port |
| `CACHE_SIZE_MB` | `2000` | osm2pgsql cache (higher = faster) |
| `NUM_PROCESSES` | `4` | Parallel processes (match CPU cores) |
| `CLEANUP` | `true` | Delete intermediate files |
| `DROP_SLIM_TABLES` | `false` | Save space (disables future updates) |
| `GEOFABRIK_BASE_URL` | `https://download.geofabrik.de` | Use local mirror if available |
| `LOG_FORMAT` | `json` | `json` for k8s, `text` for development |

### Supported Regions

`africa`, `antarctica`, `asia`, `australia-oceania`, `central-america`, `europe`, `north-america`, `south-america`, `planet`

## Development

### Local Testing

```bash
# Test with docker-compose (includes PostgreSQL)
docker compose up --build

# Test different region
OSM_REGION=asia docker compose up --build

# Clean up
docker compose down -v
```

### Build Image

```bash
docker build -t osm-ingestion:latest .
```


