from decimal import Decimal

from ...dtos.field_dto import FieldDTO
from ...dtos.total_dto import TotalDTO
from ...interfaces.unit_of_work import UnitOfWork


class ListFieldsHandler:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def handle(
        self,
        crop_name: str | None = None,
        owner_name: str | None = None,
        min_area: Decimal | None = None,
        max_area: Decimal | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> tuple[list[FieldDTO], TotalDTO]:

        fields = await self.uow.fields.get_many(
            crop_name=crop_name,
            owner_name=owner_name,
            min_area=min_area,
            max_area=max_area,
            limit=max(limit, 1),
            offset=max(offset, 0),
        )
        total = await self.uow.fields.count(
            crop_name=crop_name,
            owner_name=owner_name,
            min_area=min_area,
            max_area=max_area,
        )

        return (
            [
                FieldDTO(
                    id=str(field.id),
                    name=field.name,
                    owner_name=field.owner_name,
                    crop_name=field.crop_name,
                    area_ha=field.area_ha,
                )
                for field in fields
            ],
            TotalDTO(total),
        )
