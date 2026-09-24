import time
import uuid
from decimal import Decimal

from fastapi import APIRouter
from fastapi import HTTPException
from geoalchemy2.shape import from_shape
from geoalchemy2.shape import to_shape
from shapely.geometry import mapping
from shapely.geometry import shape

from src.core.config import settings
from src.exceptions import NotValidValidationError
from src.repositories.crop_repository import CropRepository
from src.repositories.field_repository import FieldRepository
from src.repositories.owner_repository import OwnerRepository
from src.schemas.field import FieldCreateData
from src.schemas.field import FieldResponse
from src.schemas.field import FindByPointFieldResponse
from src.schemas.field import FindByPointResponse
from src.schemas.field import GeometrySchema
from src.schemas.field import GeoPoint
from src.schemas.field import ListFieldResponse
from src.schemas.pagination import Pagination

router = APIRouter(prefix="/fields", tags=["Fields"])


@router.get("", response_model=Pagination[ListFieldResponse])
async def list_fields(
    crop: str | None = None,
    owner: str | None = None,
    min_area: Decimal | None = None,
    max_area: Decimal | None = None,
    limit: int = 10,
    offset: int = 0,
):
    limit = limit if limit > 0 else 1
    fields = await FieldRepository.get_list(
        crop_name=crop,
        owner_name=owner,
        min_area=min_area,
        max_area=max_area,
        offset=offset,
        limit=limit,
    )

    fields_count = await FieldRepository.count(
        crop_name=crop,
        owner_name=owner,
        min_area=min_area,
        max_area=max_area,
    )

    return Pagination(
        fields=[
            ListFieldResponse(
                id=field.id,
                name=field.name,
                area_ha=field.area_ha,
                crop=field.crop.name,
                owner=field.owner.name,
            )
            for field in fields],
        total=fields_count,
    )


@router.get("/find-by-point", response_model=FindByPointResponse)
async def get_fields_by_point(lat: float, lon: float):
    start_time = time.perf_counter()
    fields_with_distances = await FieldRepository.find_by_point(
        lon=lon,
        lat=lat,
    )
    elapsed_ms = (time.perf_counter() - start_time) * 1000
    return FindByPointResponse(
        query_point=GeoPoint(lon=lon, lat=lat),
        fields=[
            FindByPointFieldResponse(
                id=field_with_distance.field.id,
                name=field_with_distance.field.name,
                area_ha=field_with_distance.field.area_ha,
                crop=field_with_distance.field.crop.name,
                owner=field_with_distance.field.owner.name,
                distance_to_center_m=Decimal(f"{field_with_distance.distance_to_center_m:.1f}"),
            )
            for field_with_distance in fields_with_distances
        ],
        query_time_ms=Decimal(f"{elapsed_ms:.1f}"),
    )


@router.get("/{id}", response_model=FieldResponse)
async def get_field_by_id(id: uuid.UUID):
    field = await FieldRepository.get_by_id(id)
    if not field:
        raise HTTPException(status_code=404, detail="Field is not found")

    return FieldResponse(
        id=field.id,
        name=field.name,
        area_ha=field.area_ha,
        crop=field.crop.name,
        owner=field.owner.name,
        geometry=GeometrySchema(**mapping(to_shape(field.geometry))),
        created_at=field.created_at,
    )


@router.post("", response_model=FieldResponse, status_code=201)
async def create_filed(data: FieldCreateData):
    try:
        geom = from_shape(shape(data.geometry.model_dump()), srid=4326)
    except ValueError as e:
        raise NotValidValidationError(field_name="geometry", field_value=data.geometry, message=str(e)) from e

    geometry_validation = await FieldRepository.get_geometry_validation(geom)
    if not geometry_validation.is_valid:
        raise NotValidValidationError(
            field_name="geometry", field_value=data.geometry, message="Polygon shape is not valid",
        )

    if geometry_validation.area <= settings.AREA_MIN_SIZE:
        raise NotValidValidationError(
            field_name="geometry",
            field_value=data.geometry,
            message=f"Field area should be greater than {settings.AREA_MIN_SIZE} ha",
        )

    crop = await CropRepository.get_by_name(name=data.crop)
    owner = await OwnerRepository.get_by_name(name=data.owner)

    if not crop:
        crop = await CropRepository.create(name=data.crop)

    if not owner:
        owner = await OwnerRepository.create(name=data.owner)

    field = await FieldRepository.create(
        name=data.name,
        area_ha=geometry_validation.area,
        geometry=geom,
        owner_id=owner.id,
        crop_id=crop.id,
    )

    return FieldResponse(
        id=field.id,
        name=field.name,
        area_ha=field.area_ha,
        crop=crop.name,
        owner=owner.name,
        geometry=data.geometry,
        created_at=field.created_at,
    )
