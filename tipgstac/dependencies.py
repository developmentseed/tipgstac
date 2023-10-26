"""tipgstac dependencies."""

import datetime
from typing import Dict

from aiocache import cached
from buildpg import render
from fastapi import Path
from starlette.requests import Request
from typing_extensions import Annotated

from tipgstac.collections import Catalog, PgSTACCollection
from tipgstac.settings import CacheSettings

cache_config = CacheSettings()


@cached(
    ttl=cache_config.ttl,
    key_builder=lambda _f, request: request.app.title or "tipgstac-catalog",
)
async def CatalogParams(request: Request) -> Catalog:
    """Catalog Dependency."""
    async with request.app.state.pool.acquire() as conn:
        collections = await conn.fetchval("SELECT * FROM pgstac.all_collections();")

        catalog: Dict[str, PgSTACCollection] = {}
        for collection in collections:
            collection_id = collection["id"]
            catalog[collection_id] = PgSTACCollection(
                type="Collection",
                id=collection_id,
                table="collections",
                schema="pgstac",
                extent=collection.get("extent"),
                description=collection.get("description", None),
                id_column="id",
                stac_version=collection.get("stac_version"),
                stac_extensions=collection.get("stac_extensions", []),
            )

        return Catalog(collections=catalog, last_updated=datetime.datetime.now())


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
        collection = await conn.fetchval(q, *p)

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
            id_column="id",
            stac_queryables=queryables,
            stac_version=collection.get("stac_version"),
            stac_extensions=collection.get("stac_extensions", []),
        )
