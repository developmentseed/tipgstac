"""tipgstac.database: database events."""

from typing import Optional

import orjson
from buildpg import asyncpg

from tipg.settings import PostgresSettings

from fastapi import FastAPI


class connection_factory:
    """Connection creation."""

    async def __call__(self, conn: asyncpg.Connection):
        """Create connection."""
        await conn.set_type_codec(
            "json", encoder=orjson.dumps, decoder=orjson.loads, schema="pg_catalog"
        )
        await conn.set_type_codec(
            "jsonb", encoder=orjson.dumps, decoder=orjson.loads, schema="pg_catalog"
        )

        await conn.execute(
            """
            SELECT set_config(
                'search_path',
                'pgstac,' || current_setting('search_path', false),
                false
                );
            """
        )


async def connect_to_db(
    app: FastAPI,
    settings: Optional[PostgresSettings] = None,
    **kwargs,
) -> None:
    """Connect."""
    if not settings:
        settings = PostgresSettings()

    con_init = connection_factory()

    app.state.pool = await asyncpg.create_pool_b(
        str(settings.database_url),
        min_size=settings.db_min_conn_size,
        max_size=settings.db_max_conn_size,
        max_queries=settings.db_max_queries,
        max_inactive_connection_lifetime=settings.db_max_inactive_conn_lifetime,
        init=con_init,
        **kwargs,
    )


async def close_db_connection(app: FastAPI) -> None:
    """Close connection."""
    await app.state.pool.close()
