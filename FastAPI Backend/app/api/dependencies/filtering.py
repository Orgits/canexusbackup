from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from fastapi import Query


class FilterParams(BaseModel):
    search: Optional[str] = Field(default=None, description="Search query")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Additional filters")

    def get_filters(self, allowed_fields: List[str]) -> Dict[str, Any]:
        return {k: v for k, v in self.filters.items() if k in allowed_fields}


def get_filter_params(
    search: Optional[str] = Query(None, description="Search query"),
) -> FilterParams:
    return FilterParams(search=search)