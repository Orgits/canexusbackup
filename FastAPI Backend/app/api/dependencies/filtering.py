from typing import Any

from fastapi import Query
from pydantic import BaseModel, Field


class FilterParams(BaseModel):
    search: str | None = Field(default=None, description="Search query")
    filters: dict[str, Any] = Field(default_factory=dict, description="Additional filters")

    def get_filters(self, allowed_fields: list[str]) -> dict[str, Any]:
        return {k: v for k, v in self.filters.items() if k in allowed_fields}


def get_filter_params(
    search: str | None = Query(None, description="Search query"),
) -> FilterParams:
    return FilterParams(search=search)
