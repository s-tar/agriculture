#!/usr/bin/env python3
"""Populate the agriculture database with Ukrainian agricultural field data.

Usage (via Docker):
    docker-compose run --rm data_feed python data_feed.py --count 100

Environment variables (set in docker-compose.yml or .env):
    DATABASE_URL — set automatically by docker-compose

Field boundary geometries are downloaded from the NASA Harvest / Ukraine field
boundary dataset on harvestportal.org (CKAN), streamed to a temp file, then
parsed from GeoJSON files inside the ZIP archives. Area in hectares is
calculated via PostGIS (ST_Area + EPSG:3035 equal-area projection). Fields are
inserted in batches of 100 records per DB transaction.
"""

import argparse
import asyncio
import random
import sys
import tempfile
import uuid
import zipfile
from datetime import datetime
from datetime import timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import httpx
import shapefile
from dotenv import load_dotenv
from faker import Faker
from geoalchemy2 import WKTElement
from sqlalchemy import text

load_dotenv(Path(__file__).parent.parent / ".env")

from src.core.database import async_session_maker
from src.models.crop import Crop
from src.models.field import Field
from src.models.owner import Owner
from src.repositories.crop_repository import CropRepository
from src.repositories.field_repository import FieldRepository
from src.repositories.owner_repository import OwnerRepository

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DATASET_API = "https://harvestportal.org/api/3/action/package_show"
DATASET_ID = "ukraine-field-boundary-delineation-2023"

BATCH_SIZE = 100

CROPS = [
    "Пшениця озима",
    "Кукурудза на зерно",
    "Соняшник",
    "Ріпак озимий",
    "Ячмінь ярий",
    "Соя",
    "Цукровий буряк",
    "Горох",
    "Жито озиме",
    "Овес",
]

fake = Faker("uk_UA")


def generate_owner_name() -> str:
    if random.choice((True, False)):
        return f"{fake.last_name_male()} {fake.first_name_male()[0]}.{fake.first_name_male()[0]}."
    else:
        return f"{fake.last_name_female()} {fake.first_name_female()[0]}.{fake.first_name_male()[0]}."


# ---------------------------------------------------------------------------
# Geometry fetching
# ---------------------------------------------------------------------------


def _coords_to_wkt(ring: list) -> str:
    return "POLYGON((" + ", ".join(f"{lon} {lat}" for lon, lat in ring) + "))"


# /data is mounted from ./data on the host — persists between runs and is never tmpfs
_DATA_DIR = Path(__file__).parent.parent / "data"


def _read_wkts_from_shp(shp_path: Path) -> list[str]:
    wkts = []
    sf = shapefile.Reader(str(shp_path))
    for shape in sf.iterShapes():  # lazy: one shape at a time, no full-file load
        # 5 = Polygon, 15 = PolygonZ, 25 = PolygonM
        if shape.shapeType not in (5, 15, 25):
            continue
        if not shape.parts or not shape.points:
            continue
        # Exterior ring only: points[parts[0] : parts[1]] (or to end if one ring)
        end = shape.parts[1] if len(shape.parts) > 1 else len(shape.points)
        ring = shape.points[:end]
        wkts.append(_coords_to_wkt(ring))
    return wkts


def fetch_geometries(needed: int) -> list[str]:
    """Download ZIPs to /data (cached), extract to a temp dir, parse with pyshp."""
    _DATA_DIR.mkdir(exist_ok=True)

    print("Fetching dataset resource list from harvestportal.org...")
    with httpx.Client(timeout=60) as client:
        resp = client.get(DATASET_API, params={"id": DATASET_ID})
    resp.raise_for_status()

    data = resp.json()
    if not data.get("success"):
        raise RuntimeError(f"CKAN API error: {data.get('error')}")

    zip_urls = [
        r["url"]
        for r in data["result"]["resources"]
        if r.get("format", "").upper() == "ZIP"
    ]
    if not zip_urls:
        raise RuntimeError("No ZIP resources found in dataset")

    wkts: list[str] = []
    with httpx.Client(timeout=None, follow_redirects=True) as client:
        for i, url in enumerate(zip_urls, 1):
            filename = url.split("/")[-1]
            zip_path = _DATA_DIR / filename

            if zip_path.exists():
                print(f"  Using cached ZIP {i}/{len(zip_urls)}: {filename}")
            else:
                print(f"  Downloading ZIP {i}/{len(zip_urls)}: {url}")
                with client.stream("GET", url) as stream:
                    stream.raise_for_status()
                    with zip_path.open("wb") as f:
                        for chunk in stream.iter_bytes(chunk_size=4 * 1024 * 1024):
                            f.write(chunk)

            extract_dir = Path(tempfile.mkdtemp(dir=_DATA_DIR))
            try:
                with zipfile.ZipFile(zip_path) as zf:
                    zf.extractall(extract_dir)

                found: list[str] = []
                for shp_path in extract_dir.rglob("*.shp"):
                    found.extend(_read_wkts_from_shp(shp_path))
            finally:
                for f in extract_dir.rglob("*"):
                    if f.is_file():
                        f.unlink()
                extract_dir.rmdir()

            print(f"    {len(found)} polygon(s) extracted")
            wkts.extend(found)
            if len(wkts) >= needed:
                break

    if not wkts:
        raise RuntimeError("No polygon geometries found in dataset ZIPs.")

    return wkts


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

_crop_cache: dict[str, Crop] = {}


async def _get_or_create_crop(name: str) -> Crop:
    if name not in _crop_cache:
        crop = await CropRepository.get_by_name(name)
        if not crop:
            crop = await CropRepository.create({"name": name})
        _crop_cache[name] = crop
    return _crop_cache[name]


async def _get_or_create_owner(name: str) -> Owner:
    owner = await OwnerRepository.get_by_name(name)
    if not owner:
        owner = await OwnerRepository.create({"name": name})
    return owner


async def insert_batch(batch: list[dict]) -> None:
    """One session per batch: calculate area_ha via PostGIS, add all fields, commit once."""
    async with async_session_maker() as session:
        for item in batch:
            area_result = await session.execute(
                text(
                    "SELECT ROUND("
                    "(ST_Area(ST_Transform(ST_MakeValid(ST_GeomFromText(:wkt, 4326)), 3035)) / 10000)"
                    "::numeric, 4)",
                ),
                {"wkt": item["wkt"]},
            )
            area_ha = Decimal(str(area_result.scalar()))
            now = datetime.now(timezone.utc)
            # model_construct bypasses Pydantic so WKTElement passes through to
            # the underlying GeoAlchemy2 Geometry column without str validation.
            field = Field.model_construct(
                id=uuid.uuid4(),
                name=item["name"],
                owner_id=item["owner_id"],
                crop_id=item["crop_id"],
                area_ha=area_ha,
                geometry=WKTElement(item["wkt"], srid=4326),
                created_at=now,
                updated_at=now,
            )
            session.add(field)
        await session.commit()


# ---------------------------------------------------------------------------
# Main async runner
# ---------------------------------------------------------------------------


async def feed_data(count: int) -> None:
    start = await FieldRepository.count()

    geometries = fetch_geometries(needed=count)
    print(f"  {len(geometries)} geometries available.")

    print("Seeding crops...")
    crops = [await _get_or_create_crop(name) for name in CROPS]

    print(f"  DB has {start} field(s); new fields will be №{start + 1}–№{start + count}.")

    # Use geometries after the already-inserted ones; wrap around if exhausted.
    geo_pool = geometries[start:] if start < len(geometries) else geometries

    batch: list[dict] = []
    for i in range(count):
        owner = await _get_or_create_owner(generate_owner_name())
        batch.append(
            {
                "name": f"Поле №{start + i + 1}",
                "owner_id": owner.id,
                "crop_id": random.choice(crops).id,
                "wkt": geo_pool[i % len(geo_pool)],
            },
        )

        if len(batch) == BATCH_SIZE or (i + 1) == count:
            await insert_batch(batch)
            print(f"  {start + i + 1}/{start + count} inserted")
            batch = []

    print("Done.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed the agriculture database with fields data.",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=1000,
        help="Number of field records to insert (default: 1000)",
    )
    args = parser.parse_args()

    if args.count <= 0:
        parser.error("--count must be a positive integer")

    asyncio.run(feed_data(args.count))


if __name__ == "__main__":
    main()
