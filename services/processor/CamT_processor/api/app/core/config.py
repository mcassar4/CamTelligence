from functools import lru_cache
from typing import List

from pydantic import BaseSettings, Field


class APISettings(BaseSettings):
    app_name: str = "CamTelligence API"
    api_prefix: str = "/"
    allowed_origins: List[str] = Field(default_factory=lambda: ["*"], env="CORS_ORIGINS")
    media_root: str = Field("/data/media", env="MEDIA_ROOT")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> APISettings:
    return APISettings()
