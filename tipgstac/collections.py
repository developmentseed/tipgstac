"""tipgstac collections."""

import datetime
import re
from typing import Any, Dict, List, Optional, Tuple, TypedDict, Union
import json

from buildpg import RawDangerous as raw
from buildpg import asyncpg, clauses
from buildpg import funcs as pg_funcs
from buildpg import logic, render
from ciso8601 import parse_rfc3339
from morecantile import Tile, TileMatrixSet
from pydantic import BaseModel, Field, model_validator
from pygeofilter.ast import AstType

from tipg.errors import (
    InvalidDatetime,
    InvalidDatetimeColumnName,
    InvalidGeometryColumnName,
    InvalidLimit,
    InvalidPropertyName,
    MissingDatetimeColumn,
)
from tipg.filter.evaluate import to_filter
from tipg.filter.filters import bbox_to_wkt
from tipg.logger import logger
from tipg.model import Extent
from tipg.settings import FeaturesSettings, TableSettings
from tipg.collections import Collection, Feature, FeatureCollection

from fastapi import FastAPI

features_settings = FeaturesSettings()

from tipg.collections import Column, Parameter

class PgSTACCollection(Collection):
    """Model for DB Table and Function."""

    type: str
    id: str
    table: str
    dbschema: str = Field(..., alias="schema")
    title: Optional[str] = None
    description: Optional[str] = None
    properties: List[Column] = []
    id_column: Optional[str] = None
    geometry_column: Optional[Column] = None
    datetime_column: Optional[Column] = None
    parameters: List[Parameter] = []
    stac_extent: Optional[Extent] = None
    stac_queryables: Optional[Dict] = None

    model_config = {"extra": "allow"}

    @property
    def extent(self) -> Optional[Extent]:
        """Return extent."""
        return self.stac_extent

    @property
    def queryables(self) -> Dict:
        """Return the queryables."""
        return self.stac_queryables or {}

    @property
    def bounds(self) -> Optional[List[float]]:
        """Return spatial bounds from collection extent."""
        if self.extent and self.extent.spatial:
            return self.extent.spatial.bbox[0]

        return None

    @property
    def dt_bounds(self) -> Optional[List[str]]:
        """Return temporal bounds from collection extent."""
        if self.extent and self.extent.temporal:
            return self.extent.temporal.interval[0]

        return None

    @property
    def crs(self):
        """Return crs of set geometry column."""
        return "http://www.opengis.net/def/crs/EPSG/0/4326"

    async def features(
        self,
        pool: asyncpg.BuildPgPool,
        *,
        ids_filter: Optional[List[str]] = None,
        bbox_filter: Optional[List[float]] = None,
        datetime_filter: Optional[List[str]] = None,
        properties_filter: Optional[List[Tuple[str, str]]] = None,
        cql_filter: Optional[AstType] = None,
        sortby: Optional[str] = None,
        properties: Optional[List[str]] = None,
        geom: Optional[str] = None,
        dt: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        bbox_only: Optional[bool] = None,
        simplify: Optional[float] = None,
        geom_as_wkt: bool = False,
        function_parameters: Optional[Dict[str, str]] = None,
    ) -> Tuple[FeatureCollection, int]:
        """Build and run Pg query."""
        function_parameters = function_parameters or {}

        if geom and geom.lower() != "none" and not self.get_geometry_column(geom):
            raise InvalidGeometryColumnName(f"Invalid Geometry Column: {geom}.")

        if limit and limit > features_settings.max_features_per_query:
            raise InvalidLimit(
                f"Limit can not be set higher than the `tipg_max_features_per_query` setting of {features_settings.max_features_per_query}"
            )

        if datetime_filter:
            datetime_filter = "/".join(datetime_filter)  # type: ignore

        base_args = {
            "collections": [self.id],
            "bbox": bbox_filter,
            "datetime": datetime_filter,
            "limit": limit,
            # we use `offset` not token :-(
            # "token": token
        }
        if ids_filter:
            base_args["ids"] = ids_filter

        clean = {}
        for k, v in base_args.items():
            if v is not None and v != []:
                clean[k] = v

        # TODO: Translate other options

        async with pool.acquire() as conn:
            q, p = render(
                """
                SELECT * FROM search(:req::text::jsonb);
                """,
                req=json.dumps(clean),
            )
            fc = await conn.fetchval(q, *p)

        count = None
        if context := fc.get("context"):
            count = context.get("matched")

        return (
            FeatureCollection(type="FeatureCollection", features=fc.get("features")),
            count,  # type: ignore
        )

    async def get_tile(
        self,
        *,
        pool: asyncpg.BuildPgPool,
        **kwargs: Any,
    ):
        """Build query to get Vector Tile."""
        raise NotImplementedError


class Catalog(TypedDict):
    """Collection Catalog."""

    collections: Dict[str, PgSTACCollection]
    last_updated: datetime.datetime
