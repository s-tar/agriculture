from src.models.crop import Crop
from src.repositories.base_repository import BaseRepository


class CropRepositoryClass(BaseRepository[Crop]):
    def __init__(self):
        super().__init__(Crop)

    async def get_by_name(self, name: str) -> Crop | None:
        return await self.get(Crop.name == name)


CropRepository = CropRepositoryClass()
