from pydantic import BaseModel


class Pagination[T](BaseModel):
    total: int = 0
    fields: list[T]
