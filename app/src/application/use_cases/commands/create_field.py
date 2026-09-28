from dataclasses import dataclass

from src.config.settings import settings
from src.domain.exceptions import (
    AreaValidationError,
    InvalidCropNameError,
    InvalidGeometryError,
    InvalidOwnerNameError,
)
from src.domain.value_objects.geometry import Geometry

from ...dtos.field_dto import FieldIdDTO
from ...interfaces.unit_of_work import UnitOfWork


@dataclass
class CreateFieldCommand:
    name: str
    owner_name: str
    crop_name: str
    geometry: Geometry


class CreateFieldHandler:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def handle(self, command: CreateFieldCommand) -> FieldIdDTO:
        if not command.crop_name:
            raise InvalidCropNameError("Crop name is not provided")

        if not command.owner_name:
            raise InvalidOwnerNameError("Owner name is not provided")

        detailed_geometry = await self.uow.fields.get_geometry_details(
            geometry=command.geometry,
        )

        if not detailed_geometry.is_valid:
            raise InvalidGeometryError("Field geometry is not valid")

        if detailed_geometry.area_ha <= settings.AREA_MIN_SIZE:
            raise AreaValidationError(
                f"Field area is too small. Should be bigger then {settings.AREA_MIN_SIZE} hectares)"
            )

        field = await self.uow.fields.create(
            name=command.name,
            owner_name=command.owner_name,
            crop_name=command.crop_name,
            geometry=command.geometry,
        )

        await self.uow.commit()

        return FieldIdDTO(
            id=str(field.id),
        )
