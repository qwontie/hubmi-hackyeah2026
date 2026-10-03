from typing import Any, cast

from sqlalchemy import ColumnElement


def cosine_distance(column: object, vector: list[float]) -> ColumnElement[float]:
    return cast("Any", column).cosine_distance(vector)
