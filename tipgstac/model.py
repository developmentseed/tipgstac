"""
tipgstac models.

Note: This is mostly a copy of https://github.com/stac-utils/stac-fastapi/blob/master/stac_fastapi/pgstac/stac_fastapi/pgstac/types/search.py
"""

from typing import Any, Dict, List, Literal, Optional, Set

from geojson_pydantic.geometries import Geometry
from geojson_pydantic.types import BBox
from pydantic import BaseModel, Field, ValidationInfo, field_validator, model_validator

# ref: https://github.com/stac-api-extensions/query
# TODO: add "startsWith", "endsWith", "contains", "in"
Operator = Literal["eq", "neq", "lt", "lte", "gt", "gte"]

# ref: https://github.com/radiantearth/stac-api-spec/tree/master/fragments/filter#get-query-parameters-and-post-json-fields
FilterLang = Literal["cql-json", "cql-text", "cql2-json"]


class PgSTACSearch(BaseModel):
    """Search Query model."""

    collections: Optional[List[str]] = None
    ids: Optional[List[str]] = None
    bbox: Optional[BBox] = None
    intersects: Optional[Geometry] = None
    query: Optional[Dict[str, Dict[Operator, Any]]] = None
    filter: Optional[Dict] = None
    datetime: Optional[str] = None
    sortby: Optional[Any] = None
    fields: Optional[Dict[str, Set]] = None
    filter_lang: Optional[FilterLang] = Field(default=None, alias="filter-lang")
    limit: Optional[int] = None

    model_config = {"extra": "allow"}

    @model_validator(mode="before")
    def validate_query_fields(cls, values: Dict) -> Dict:
        """Pgstac does not require the base validator for query fields."""
        return values

    @field_validator("datetime")
    def validate_datetime(cls, v):
        """Pgstac does not require the base validator for datetime."""
        return v

    @field_validator("intersects")
    def validate_spatial(cls, v: Optional[Geometry], info: ValidationInfo):
        """Make sure bbox is not used with Intersects."""
        if v and info.data["bbox"]:
            raise ValueError("intersects and bbox parameters are mutually exclusive")

        return v

    @field_validator("bbox")
    def validate_bbox(cls, v: BBox):
        """Validate BBOX."""
        if v:
            # Validate order
            if len(v) == 4:
                xmin, ymin, xmax, ymax = v
            else:
                xmin, ymin, min_elev, xmax, ymax, max_elev = v
                if max_elev < min_elev:
                    raise ValueError(
                        "Maximum elevation must greater than minimum elevation"
                    )

            if xmax < xmin:
                raise ValueError(
                    "Maximum longitude must be greater than minimum longitude"
                )

            if ymax < ymin:
                raise ValueError(
                    "Maximum longitude must be greater than minimum longitude"
                )

            # Validate against WGS84
            if xmin < -180 or ymin < -90 or xmax > 180 or ymax > 90:
                raise ValueError("Bounding box must be within (-180, -90, 180, 90)")

        return v
