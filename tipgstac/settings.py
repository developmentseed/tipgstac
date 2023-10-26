"""tipgstac config."""

import pathlib
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings


class APISettings(BaseSettings):
    """API settings"""

    name: str = "TiPg STAC: Use PgSTAC as backend"
    debug: bool = False
    cors_origins: str = "*"
    cachecontrol: str = "public, max-age=3600"
    template_directory: Optional[str] = None

    # catalog_ttl: int = 300

    model_config = {"env_prefix": "TIPG_STAC_", "env_file": ".env", "extra": "ignore"}

    @field_validator("cors_origins")
    def parse_cors_origin(cls, v):
        """Parse CORS origins."""
        return [origin.strip() for origin in v.split(",")]

