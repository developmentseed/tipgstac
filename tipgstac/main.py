"""tipgstac app."""

from contextlib import asynccontextmanager

import jinja2
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.templating import Jinja2Templates
from starlette_cramjam.middleware import CompressionMiddleware

from tipg.errors import DEFAULT_STATUS_CODES, add_exception_handlers
from tipg.middleware import CacheControlMiddleware
from tipg.settings import PostgresSettings
from tipgstac import __version__ as tipg_version
from tipgstac.database import close_db_connection, connect_to_db
from tipgstac.factory import OGCFeaturesFactory
from tipgstac.settings import APISettings

settings = APISettings()
postgres_settings = PostgresSettings()


templates = Jinja2Templates(  # type: ignore
    directory="",
    loader=jinja2.ChoiceLoader(
        [
            jinja2.PackageLoader("tipgstac", "templates"),
            jinja2.PackageLoader("tipg", "templates"),
        ]
    ),
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI Lifespan."""
    # Create Connection Pool
    await connect_to_db(app, settings=postgres_settings)
    yield
    # Close the Connection Pool
    await close_db_connection(app)


app = FastAPI(
    title=settings.name,
    version=tipg_version,
    openapi_url="/api",
    docs_url="/api.html",
    lifespan=lifespan,
)

ogc_api = OGCFeaturesFactory(title=settings.name, templates=templates)
app.include_router(ogc_api.router)

# Set all CORS enabled origins
if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

app.add_middleware(CacheControlMiddleware, cachecontrol=settings.cachecontrol)
app.add_middleware(CompressionMiddleware)

add_exception_handlers(app, DEFAULT_STATUS_CODES)


@app.get(
    "/healthz",
    description="Health Check.",
    summary="Health Check.",
    operation_id="healthCheck",
    tags=["Health Check"],
)
def ping():
    """Health check."""
    return {"ping": "pong!"}
