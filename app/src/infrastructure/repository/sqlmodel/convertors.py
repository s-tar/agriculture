from geoalchemy2 import WKBElement
from geoalchemy2.shape import from_shape, to_shape
from shapely import get_coordinates
from shapely.geometry import shape
from src.domain.entities.field import Field
from src.domain.value_objects.field_id import FieldId
from src.domain.value_objects.geometry import Geometry, GeometryType, Point

from .models.field import Field as FieldModel


def field_model_to_entity(field: FieldModel) -> Field:
    geometry_shape = to_shape(field.geometry)

    return Field(
        id=FieldId(str(field.id)),
        name=field.name,
        owner_name=field.owner.name,
        crop_name=field.crop.name,
        area_ha=field.area_ha,
        geometry=Geometry(
            type=GeometryType(geometry_shape.geom_type),
            coordinates=[
                Point(lon, lat) for lon, lat in get_coordinates(geometry_shape).tolist()
            ],
        ),
        created_at=field.created_at,
        updated_at=field.updated_at,
    )


def geometry_to_wkb(geometry: Geometry, srid: int) -> WKBElement:
    print(
        {
            "type": str(geometry.type),
            "coordinates": [(point.lat, point.lon) for point in geometry.coordinates],
        }
    )
    return from_shape(
        shape(
            {
                "type": str(geometry.type),
                "coordinates": [
                    [(point.lat, point.lon) for point in geometry.coordinates],
                ],
            }
        ),
        srid=srid,
    )
