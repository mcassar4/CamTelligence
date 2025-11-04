from datetime import timedelta

from pydantic import BaseSettings, Field


class JanitorSettings(BaseSettings):
    retention_days: int = Field(14, env="RETENTION_DAYS")
    retention_enabled: bool = Field(True, env="RETENTION_ENABLED")
    retention_interval_seconds: int = Field(3600, env="RETENTION_INTERVAL_SECONDS")
    media_root: str = Field("/data/media", env="MEDIA_ROOT")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def retention_window(self) -> timedelta:
        return timedelta(days=max(0, self.retention_days))
