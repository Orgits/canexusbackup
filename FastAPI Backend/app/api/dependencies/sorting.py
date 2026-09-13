from typing import List, Optional
from pydantic import BaseModel, Field
from fastapi import Query


class SortParams(BaseModel):
    sort_by: Optional[str] = Field(default=None, description="Field to sort by")
    sort_order: str = Field(default="asc", pattern="^(asc|desc)$", description="Sort order")

    def get_sort_clause(self, allowed_fields: List[str]) -> Optional[str]:
        if self.sort_by and self.sort_by in allowed_fields:
            order = "DESC" if self.sort_order == "desc" else "ASC"
            return f"{self.sort_by} {order}"
        return None


def get_sort_params(
    sort_by: Optional[str] = Query(None, description="Field to sort by"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$", description="Sort order"),
) -> SortParams:
    return SortParams(sort_by=sort_by, sort_order=sort_order)