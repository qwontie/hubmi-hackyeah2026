from pydantic import BaseModel

MAX_PER_PAGE = 100


class Page[T](BaseModel):
    items: list[T]
    total: int
    page: int
    per_page: int


def offset(page: int, per_page: int) -> int:
    return (page - 1) * per_page
