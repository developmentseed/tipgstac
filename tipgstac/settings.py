"""tipgstac config."""

from typing import Optional

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings


class APISettings(BaseSettings):
    """API settings"""

    name: str = "TiPg STAC: Use PgSTAC as backend"
    debug: bool = False
    cors_origins: str = "*"
    cachecontrol: str = "public, max-age=3600"
    template_directory: Optional[str] = None

    model_config = {"env_prefix": "TIPG_STAC_", "env_file": ".env", "extra": "ignore"}

    @field_validator("cors_origins")
    def parse_cors_origin(cls, v):
        """Parse CORS origins."""
        return [origin.strip() for origin in v.split(",")]


class CacheSettings(BaseSettings):
    """Cache settings"""

    # TTL of the cache in seconds
    ttl: int = 300

    # Whether or not caching is enabled
    disable: bool = False

    model_config = {"env_prefix": "TIPG_STAC_CACHE_", "env_file": ".env"}

    @model_validator(mode="after")
    def check_enable(self):
        """Check if cache is disabled."""
        if self.disable:
            self.ttl = 0

        return self
