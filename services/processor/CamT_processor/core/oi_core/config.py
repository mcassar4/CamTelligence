from functools import lru_cache
from typing import Optional

from pydantic import BaseSettings, Field, validator


class DatabaseSettings(BaseSettings):
    db_host: str = Field("postgres", env="DB_HOST")
    db_port: int = Field(5432, env="DB_PORT")
    db_user: str = Field("oi", env="DB_USER")
    db_password: str = Field("oi_pass", env="DB_PASSWORD")
    db_name: str = Field("intelligence", env="DB_DATABASE")
    db_pool_size: int = Field(10, env="DB_POOL_SIZE")
    db_max_overflow: int = Field(20, env="DB_MAX_OVERFLOW")
    db_echo: bool = Field(False, env="DB_ECHO")
    db_uri: Optional[str] = Field(None, env="DATABASE_URL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @validator("db_uri", pre=True)
    def _normalize_uri(cls, value: Optional[str], values: dict) -> Optional[str]:
        if value:
            return value
        host = values.get("db_host")
        port = values.get("db_port")
        user = values.get("db_user")
        password = values.get("db_password")
        name = values.get("db_name")
        return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}"


@lru_cache()
def get_db_settings() -> DatabaseSettings:
    return DatabaseSettings()
