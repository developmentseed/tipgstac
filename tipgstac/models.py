"""
tipgstac models.

Note: This is mostly a copy of https://github.com/stac-utils/stac-fastapi/blob/master/stac_fastapi/pgstac/stac_fastapi/pgstac/types/search.py
"""

from typing import Any, Dict, List, Literal, Optional, Set

from geojson_pydantic.geometries import Geometry
from geojson_pydantic.types import BBox
from pydantic import BaseModel, Field, ValidationInfo, field_validator
from typing_extensions import Annotated

from tipg import model

# ref: https://github.com/stac-api-extensions/query
# TODO: add "startsWith", "endsWith", "contains", "in"
Operator = Literal["eq", "neq", "lt", "lte", "gt", "gte"]

# ref: https://github.com/radiantearth/stac-api-spec/tree/master/fragments/filter#get-query-parameters-and-post-json-fields
FilterLang = Literal["cql-json", "cql-text", "cql2-json"]


class ItemsSearch(BaseModel):
    """PgSTAC Item Search Query model."""

    collections: Optional[List[str]] = None
    ids: Optional[List[str]] = None
    bbox: Optional[BBox] = None
    intersects: Optional[Geometry] = None
    query: Optional[Dict[str, Dict[Operator, Any]]] = None
    filter: Optional[Dict] = None
    datetime: Optional[str] = None
    sortby: Optional[Any] = None
    fields: Optional[Dict[str, Set]] = None
    filter_lang: Annotated[Optional[FilterLang], Field(alias="filter-lang")] = None
    limit: Optional[int] = None
    token: Optional[str] = None

    model_config = {"extra": "ignore"}

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


class CollectionsSearch(BaseModel):
    """PgSTAC Collections Search Query model."""

    ids: Optional[List[str]] = None
    bbox: Optional[BBox] = None
    intersects: Optional[Geometry] = None
    query: Optional[Dict[str, Dict[Operator, Any]]] = None
    filter: Optional[Dict] = None
    datetime: Optional[str] = None
    sortby: Optional[Any] = None
    fields: Optional[Dict[str, Set]] = None
    filter_lang: Annotated[Optional[FilterLang], Field(alias="filter-lang")] = None
    limit: Optional[int] = None
    offset: Optional[int] = None
    conf: Optional[Dict] = None

    model_config = {"extra": "ignore"}

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


class PostLink(model.Link):
    """Custom Link model for POST responses.

    Ref: https://github.com/opengeospatial/ogcapi-tiles/blob/master/openapi/schemas/common-core/link.yaml

    Code generated using https://github.com/koxudaxi/datamodel-code-generator/
    """

    body: Annotated[
        Dict,
        Field(
            description="Supplies the body parameter for Post request.",
            example={"token": "a"},
        ),
    ]

    model_config = {"use_enum_values": True}


class PostItems(model.FeatureCollection):
    """Items model for POST endpoint

    Ref: http://schemas.opengis.net/ogcapi/features/part1/1.0/openapi/schemas/featureCollectionGeoJSON.yaml

    """

    id: str
    title: Optional[str] = None
    description: Optional[str] = None
    keywords: Optional[List[str]] = None
    features: List[model.Item]
    links: Optional[List[PostLink]] = None
    timeStamp: Optional[str] = None
    numberMatched: Optional[int] = None
    numberReturned: Optional[int] = None

    model_config = {"arbitrary_types_allowed": True}

    def json_seq(self, **kwargs):
        """return a GeoJSON sequence representation."""
        for f in self.features:
            yield f.json(**kwargs) + "\n"
