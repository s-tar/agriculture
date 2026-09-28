import time

from ...dtos.distance_dto import DistanceDTO
from ...dtos.execution_time_dto import ExecutionTimeMsDTO
from ...dtos.field_dto import FieldWithDistanceToCenterDTO
from ...interfaces.unit_of_work import UnitOfWork


class GetFieldByPointHandler:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def handle(
        self,
        lat: float,
        lon: float,
    ) -> tuple[list[FieldWithDistanceToCenterDTO], ExecutionTimeMsDTO]:
        start_time = time.perf_counter()
        result = await self.uow.fields.find_by_point(lat=lat, lon=lon)
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        return (
            [
                FieldWithDistanceToCenterDTO(
                    id=str(field.id),
                    name=field.name,
                    owner_name=field.owner_name,
                    crop_name=field.crop_name,
                    area_ha=field.area_ha,
                    distance_to_center_m=DistanceDTO(float(distance)),
                )
                for field, distance in result
            ],
            ExecutionTimeMsDTO(elapsed_ms),
        )
