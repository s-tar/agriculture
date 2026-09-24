# Agriculture Field Management API

REST API for managing agricultural fields with geospatial support. Each field is stored as a PostGIS polygon and linked to a crop type and an owner.

## Tech stack

| Layer | Technology |
|---|---|
| API | FastAPI + Uvicorn |
| ORM | SQLModel / SQLAlchemy (async) + asyncpg |
| Spatial | GeoAlchemy2 + PostGIS 3.6 |
| Database | PostgreSQL 18 |
| Migrations | Alembic |

## Project structure

```
agriculture/
├── docker-compose.yml
├── .env.example
└── app/
    ├── Dockerfile
    ├── main.py               # FastAPI entry point
    ├── requirements.txt
    ├── alembic/              # migrations
    ├── seed.py               # CLI seeder (SQLModel, configurable counts)
    └── src/
        ├── core/             # config, async DB session
        ├── models/           # Crop, Owner, Field (SQLModel)
        ├── repositories/     # async repository layer
        ├── routers/          # API route handlers
        └── schemas/          # Pydantic request/response schemas
```

## Running the project

### 1. Configure environment

```bash
cp .env.example .env
```

`.env` variables:

| Variable | Default | Description |
|---|---|---|
| `PROJECT_NAME` | `Agriculture` | Application name |
| `ENVIRONMENT` | `local` | `local` / `development` / `production` |
| `POSTGRES_USER` | `postgres` | PostgreSQL user |
| `POSTGRES_PASSWORD` | `postgres` | PostgreSQL password |
| `POSTGRES_DB` | `agriculture` | Database name |

### 2. Start services

```bash
docker compose up --build
```

On startup the app container automatically runs `alembic upgrade head` before launching Uvicorn.

| Service | URL |
|---|---|
| API | http://localhost:8000 |
| Interactive docs | http://localhost:8000/docs |
| PostgreSQL | `localhost:5433` |

### 3. Seed the database

```bash
# inside the container
docker compose exec app  python seed.py \
--fields 1000 \
--spawn-point 49.03894602802728 28.1052090853511 \
--spawn-radius 30000
```

- `--fields` - number of fields to generate (default: 1000)
- `--spawn-point LAT LON` - center point around which fields are placed; if omitted, each field gets a random location within Ukraine
- `--spawn-radius METERS` - radius in meters around the spawn point within which field centers are distributed (default: 10km)

## API reference

Base path: `/api`

### Fields

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/fields` | List fields with optional filters |
| `GET` | `/api/fields/{id}` | Field detail including GeoJSON geometry |
| `POST` | `/api/fields` | Create a new field |
| `GET` | `/api/fields/find-by-point` | Fields whose polygon contains a given point |

#### `GET /api/fields` — query parameters

| Param | Type | Description |
|---|---|---|
| `crop` | string | Filter by crop name |
| `owner` | string | Filter by owner name |
| `min_area` | float | Minimum area in hectares |
| `max_area` | float | Maximum area in hectares |
| `limit` | int | Page size (default 10) |
| `offset` | int | Page offset |

#### `GET /api/fields/find-by-point` — query parameters

| Param | Type | Description |
|---|---|---|
| `lat` | float | Latitude (WGS 84) |
| `lon` | float | Longitude (WGS 84) |

Returns all fields whose polygon contains the point, plus the distance in metres from the point to each field's centroid and the query execution time.

#### `POST /api/fields` — request body

```json
{
  "name": "Поле №1",
  "geometry": {
    "type": "Polygon",
    "coordinates": [[[30.5, 48.2], [30.6, 48.2], [30.6, 48.3], [30.5, 48.3], [30.5, 48.2]]]
  },
  "crop": "Соняшник",
  "owner": "Коваленко А.С."
}
```

The server validates that the geometry is a valid PostGIS polygon and that its area is at least `0.1 ha`.

## Local development (without Docker)

```bash
# PostgreSQL must be reachable on localhost:5433
export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5433/agriculture
export ENVIRONMENT=local
export PROJECT_NAME=Agriculture

cd app
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --reload
```