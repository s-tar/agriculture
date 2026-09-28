from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from src.application.use_cases.commands.create_field import (
    CreateFieldCommand,
    CreateFieldHandler,
)
from src.application.use_cases.queries.find_fields_by_point import (
    GetFieldByPointHandler,
)
from src.application.use_cases.queries.get_field import GetFieldHandler
from src.application.use_cases.queries.list_fields import ListFieldsHandler
from src.domain.exceptions import (
    AreaValidationError,
    FieldNotFoundError,
    InvalidCropNameError,
    InvalidGeometryError,
    InvalidOwnerNameError,
)
from src.domain.value_objects.geometry import Geometry, Point
from src.domain.value_objects.geometry import GeometryType as DomainGeometryType
from src.infrastructure.api.dependancies import (
    get_create_field_handler,
    get_get_field_by_point_handler,
    get_get_field_handler,
    get_list_fields_handler,
)
from src.infrastructure.api.exceptions import ValidationError
from src.infrastructure.api.schemas.field import (
    CreateFieldResponse,
    FieldCreateData,
    FieldResponse,
    FindByPointFieldResponse,
    FindByPointResponse,
    GeometrySchema,
    GeometryType,
    GeoPoint,
    ListFieldResponse,
)
from src.infrastructure.api.schemas.pagination import Pagination

router = APIRouter(prefix="/fields", tags=["Fields"])


@router.get("", response_model=Pagination[ListFieldResponse])
async def list_fields(
    handler: Annotated[ListFieldsHandler, Depends(get_list_fields_handler)],
    crop: str | None = None,
    owner: str | None = None,
    min_area: Decimal | None = None,
    max_area: Decimal | None = None,
    limit: int = 10,
    offset: int = 0,
):
    fields, total = await handler.handle(
        crop_name=crop,
        owner_name=owner,
        min_area=min_area,
        max_area=max_area,
        limit=limit,
        offset=offset,
    )

    return Pagination(
        fields=[
            ListFieldResponse(
                id=field.id,
                name=field.name,
                area_ha=field.area_ha,
                crop=field.crop_name,
                owner=field.owner_name,
            )
            for field in fields
        ],
        total=total,
    )


@router.get("/find-by-point", response_model=FindByPointResponse)
async def get_fields_by_point(
    handler: Annotated[GetFieldByPointHandler, Depends(get_get_field_by_point_handler)],
    lat: float,
    lon: float,
):
    fields, execution_time = await handler.handle(lat, lon)
    return FindByPointResponse(
        query_point=GeoPoint(lon=lon, lat=lat),
        fields=[
            FindByPointFieldResponse(
                id=field.id,
                name=field.name,
                area_ha=field.area_ha,
                crop=field.crop_name,
                owner=field.owner_name,
                distance_to_center_m=Decimal(f"{field.distance_to_center_m:.1f}"),
            )
            for field in fields
        ],
        query_time_ms=Decimal(f"{execution_time:.1f}"),
    )


@router.get("/{id}", response_model=FieldResponse)
async def get_field_by_id(
    handler: Annotated[GetFieldHandler, Depends(get_get_field_handler)],
    id: UUID,
):
    try:
        field = await handler.handle(str(id))
    except FieldNotFoundError:
        raise HTTPException(status_code=404, detail="Field is not found")

    return FieldResponse(
        id=field.id,
        name=field.name,
        area_ha=field.area_ha,
        crop=field.crop_name,
        owner=field.owner_name,
        geometry=GeometrySchema(
            type=GeometryType(field.geometry.type),
            coordinates=[
                [(point.lat, point.lon) for point in field.geometry.coordinates]
            ],
        ),
        created_at=field.created_at,
    )


@router.post("", response_model=CreateFieldResponse, status_code=201)
async def create_field(
    handler: Annotated[CreateFieldHandler, Depends(get_create_field_handler)],
    data: FieldCreateData,
):
    command = CreateFieldCommand(
        name=data.name,
        owner_name=data.owner,
        crop_name=data.crop,
        geometry=Geometry(
            type=DomainGeometryType(data.geometry.type.value),
            coordinates=[
                Point(lat=lat, lon=lon) for lat, lon in data.geometry.coordinates[0]
            ],
        ),
    )
    try:
        field = await handler.handle(command)
    except InvalidCropNameError as e:
        raise ValidationError(field_name="crop", message=str(e)) from e
    except InvalidOwnerNameError as e:
        raise ValidationError(field_name="owner", message=str(e)) from e
    except (InvalidGeometryError, AreaValidationError) as e:
        raise ValidationError(field_name="geometry", message=str(e)) from e

    return CreateFieldResponse(
        id=field.id,
    )
