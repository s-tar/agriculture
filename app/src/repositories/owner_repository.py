from src.models.owner import Owner
from src.repositories.base_repository import BaseRepository


class OwnerRepositoryClass(BaseRepository[Owner]):
    def __init__(self):
        super().__init__(Owner)

    async def get_by_name(self, name: str) -> Owner | None:
        return await self.get(Owner.name == name)


OwnerRepository = OwnerRepositoryClass()
