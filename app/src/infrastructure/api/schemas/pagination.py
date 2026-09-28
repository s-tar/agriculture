from pydantic import BaseModel


class Pagination[T](BaseModel):
    fields: list[T]
    total: int = 0
