from src.domain.exceptions import FieldNotFoundError

from ...dtos.field_dto import FieldDetailedDTO
from ...dtos.geometry_dto import GeometryDTO, PointDTO
from ...interfaces.unit_of_work import UnitOfWork


class GetFieldHandler:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def handle(self, field_id: str) -> FieldDetailedDTO:
        field = await self.uow.fields.get(field_id)

        if not field:
            raise FieldNotFoundError(f"Field {field_id} not found")

        return FieldDetailedDTO(
            id=str(field.id),
            name=field.name,
            owner_name=field.owner_name,
            crop_name=field.crop_name,
            geometry=GeometryDTO(
                type=str(field.geometry.type.value),
                coordinates=[
                    PointDTO(lon=point.lon, lat=point.lat)
                    for point in field.geometry.coordinates
                ],
            ),
            area_ha=field.area_ha,
            created_at=field.created_at,
            updated_at=field.updated_at,
        )
