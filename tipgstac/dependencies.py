"""tipgstac dependencies."""

import json
import re
from typing import List, Literal, Optional, get_args

from aiocache import cached
from buildpg import render
from ciso8601 import parse_rfc3339
from fastapi import Depends, HTTPException, Path, Query
from pygeofilter.ast import AstType
from pygeofilter.backends.cql2_json import to_cql2
from starlette.requests import Request
from typing_extensions import Annotated

from tipg.dependencies import (
    accept_media_type,
    bbox_query,
    datetime_query,
    filter_query,
    ids_query,
    sortby_query,
)
from tipg.errors import InvalidDatetime
from tipg.resources.enums import MediaType
from tipgstac.collections import CollectionList, PgSTACCollection
from tipgstac.models import CollectionsSearch
from tipgstac.settings import CacheSettings

cache_config = CacheSettings()

PostSearchResponseType = Literal["geojson", "json", "csv", "geojsonseq", "ndjson"]


def collections_query(
    collections: Annotated[
        Optional[str], Query(description="Filter by Collections.")
    ] = None,
) -> Optional[List[str]]:
    """Collections dependency."""
    return collections.split(",") if collections else None


def PostSearchOutputType(
    request: Request,
    f: Annotated[
        Optional[PostSearchResponseType],
        Query(
            description="Response MediaType. Defaults to endpoint's default or value defined in `accept` header."
        ),
    ] = None,
) -> Optional[MediaType]:
    """Output MediaType: geojson, json, csv, geojsonseq, ndjson."""
    if f:
        return MediaType[f]

    accepted_media = [MediaType[v] for v in get_args(PostSearchResponseType)]
    return accept_media_type(request.headers.get("accept", ""), accepted_media)


@cached(
    ttl=cache_config.ttl,
    key_builder=lambda _f, request, **kwargs: str(request.query_params),
)
async def CollectionsParams(  # noqa: C901
    request: Request,
    ids_filter: Annotated[Optional[List[str]], Depends(ids_query)],
    bbox_filter: Annotated[Optional[List[float]], Depends(bbox_query)],
    datetime_filter: Annotated[Optional[List[str]], Depends(datetime_query)],
    sortby: Annotated[Optional[str], Depends(sortby_query)],
    cql_filter: Annotated[Optional[AstType], Depends(filter_query)],
    limit: Annotated[
        Optional[int],
        Query(
            ge=0,
            le=1000,
            description="Limits the number of collection in the response.",
        ),
    ] = None,
    offset: Annotated[
        Optional[int],
        Query(
            ge=0,
            description="Starts the response at an offset.",
        ),
    ] = None,
) -> CollectionList:
    """Return Collections Catalog."""
    limit = limit or 10
    offset = offset or 0

    base_args = {
        "ids": ids_filter,
        "bbox": bbox_filter,
        "limit": limit,
        "offset": offset,
        "conf": {"base_url": str(request.base_url)},
    }

    if datetime_filter:
        if len(datetime_filter) == 2:
            start = (
                parse_rfc3339(datetime_filter[0])
                if datetime_filter[0] not in ["..", ""]
                else None
            )
            end = (
                parse_rfc3339(datetime_filter[1])
                if datetime_filter[1] not in ["..", ""]
                else None
            )

            if start is None and end is None:
                raise InvalidDatetime(
                    "Double open-ended datetime intervals are not allowed."
                )

            if start is not None and end is not None and start > end:
                raise InvalidDatetime("Start datetime cannot be before end datetime.")

        datetime_filter = "/".join(datetime_filter)  # type: ignore
        base_args["datetime"] = datetime_filter

    if sortby:
        sort_param = []
        for s in sortby.strip().split(","):
            if part := re.match("^(?P<direction>[+-]?)(?P<prop>.*)$", s):
                parts = part.groupdict()
                direction = parts["direction"]
                prop = parts["prop"].strip()
                sort_param.append(
                    {
                        "field": prop,
                        "direction": "desc" if direction == "-" else "asc",
                    }
                )

        base_args["sortby"] = sort_param

    if cql_filter:
        base_args["filter"] = json.loads(to_cql2(cql_filter))
        base_args["filter-lang"] = "cql2-json"

    clean = {}
    for k, v in base_args.items():
        if v is not None and v != []:
            clean[k] = v

    search = CollectionsSearch.model_validate(base_args)
    collections: List[PgSTACCollection] = []

    async with request.app.state.pool.acquire() as conn:
        q, p = render(
            """
            SELECT * FROM pgstac.collection_search(:req::text::jsonb);
            """,
            req=search.model_dump_json(exclude_none=True, by_alias=True),
        )
        results = await conn.fetchval(q, *p)

    matched = None
    if context := results.get("context"):
        matched = context.get("matched")

    for collection in results.get("collections", []):
        collections.append(
            PgSTACCollection(
                type="Collection",
                id=collection["id"],
                table="collections",
                schema="pgstac",
                extent=collection.get("extent"),
                description=collection.get("description", None),
                stac_version=collection.get("stac_version"),
                stac_extensions=collection.get("stac_extensions", []),
            ),
        )

    returned = len(collections)

    return CollectionList(
        collections=collections,
        matched=matched,
        next=offset + returned if matched - returned > offset else None,
        prev=max(offset - limit, 0) if offset else None,
    )


@cached(
    ttl=cache_config.ttl,
    key_builder=lambda _f, request, collectionId: collectionId,
)
async def CollectionParams(
    request: Request,
    collectionId: Annotated[str, Path(description="Collection identifier")],
) -> PgSTACCollection:
    """Collection Dependency."""
    async with request.app.state.pool.acquire() as conn:
        q, p = render(
            """
            WITH t AS (
                SELECT
                    *
                FROM
                    pgstac.get_collection(:id::text) c,
                    pgstac.get_queryables(:id::text) q
            )
            SELECT
                COALESCE(c || jsonb_build_object('queryables', q))
            FROM t;
            """,
            id=collectionId,
        )
        try:
            collection = await conn.fetchval(q, *p)
        except Exception:  # TODO: better error handling
            collection = None
            pass

        if not collection:
            raise HTTPException(
                status_code=404, detail=f"Collection '{collectionId}' not found."
            )

        queryables = None
        if collection.get("queryables"):
            queryables = collection["queryables"].get("properties")

        return PgSTACCollection(
            type="Collection",
            id=collection["id"],
            table="collections",
            schema="pgstac",
            stac_extent=collection.get("extent"),
            description=collection.get("description", None),
            stac_queryables=queryables,
            stac_version=collection.get("stac_version"),
            stac_extensions=collection.get("stac_extensions", []),
        )
