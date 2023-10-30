"""tipgstac.database.

Simplified version of tipg.database because we will only connect to the PgSTAC schema.

"""

from typing import Optional

import orjson
from buildpg import asyncpg
from fastapi import FastAPI

from tipg.settings import PostgresSettings


async def con_init(conn):
    """Use orjson for json returns."""
    await conn.set_type_codec(
        "json",
        encoder=orjson.dumps,
        decoder=orjson.loads,
        schema="pg_catalog",
    )
    await conn.set_type_codec(
        "jsonb",
        encoder=orjson.dumps,
        decoder=orjson.loads,
        schema="pg_catalog",
    )


async def connect_to_db(
    app: FastAPI,
    settings: Optional[PostgresSettings] = None,
    **kwargs,
) -> None:
    """Connect."""
    if not settings:
        settings = PostgresSettings()

    app.state.pool = await asyncpg.create_pool_b(
        str(settings.database_url),
        min_size=settings.db_min_conn_size,
        max_size=settings.db_max_conn_size,
        max_queries=settings.db_max_queries,
        max_inactive_connection_lifetime=settings.db_max_inactive_conn_lifetime,
        init=con_init,
        server_settings={
            "search_path": "pgstac,public",
            "application_name": "pgstac",
        },
        **kwargs,
    )


async def close_db_connection(app: FastAPI) -> None:
    """Close connection."""
    await app.state.pool.close()
