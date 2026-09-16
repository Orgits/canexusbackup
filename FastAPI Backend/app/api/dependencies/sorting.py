
from fastapi import Query
from pydantic import BaseModel, Field


class SortParams(BaseModel):
    sort_by: str | None = Field(default=None, description="Field to sort by")
    sort_order: str = Field(default="asc", pattern="^(asc|desc)$", description="Sort order")

    def get_sort_clause(self, allowed_fields: list[str]) -> str | None:
        if self.sort_by and self.sort_by in allowed_fields:
            order = "DESC" if self.sort_order == "desc" else "ASC"
            return f"{self.sort_by} {order}"
        return None


def get_sort_params(
    sort_by: str | None = Query(None, description="Field to sort by"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$", description="Sort order"),
) -> SortParams:
    return SortParams(sort_by=sort_by, sort_order=sort_order)
