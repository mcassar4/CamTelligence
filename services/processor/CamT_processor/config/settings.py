from typing import List, Optional

from pydantic import BaseSettings, Field




class ProcessorSettings(BaseSettings):
    camera_sources_raw: str = Field("", env="CAMERA_SOURCES")
    frame_poll_interval: float = Field(1.0, env="FRAME_POLL_INTERVAL")
    queue_size: int = Field(512, env="QUEUE_SIZE")
    motion_history: int = Field(200, env="MOTION_HISTORY")
    motion_kernel_size: int = Field(5, env="MOTION_KERNEL_SIZE")
    motion_min_area: int = Field(1500, env="MOTION_MIN_AREA")
    motion_debug_dir: str = Field("/data/motion_results", env="MOTION_DEBUG_DIR")
    motion_max_foreground_ratio: float = Field(0.1, env="MOTION_MAX_FOREGROUND_RATIO")
    media_root: str = Field("/data/media", env="MEDIA_ROOT")
    input_root: str = Field("/data/input", env="INPUT_ROOT")
    notification_debounce_seconds: int = Field(60, env="NOTIFICATION_DEBOUNCE_SECONDS")
    notifications_enabled: bool = Field(True, env="NOTIFICATIONS_ENABLED")
    telegram_bot_token: Optional[str] = Field(None, env="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: Optional[str] = Field(None, env="TELEGRAM_CHAT_ID")
    use_gpu: bool = Field(False, env="USE_GPU")
    api_base_url: str = Field("http://api:8000", env="API_BASE_URL")
    heartbeat_interval: int = Field(30, env="HEARTBEAT_INTERVAL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def camera_sources(self) -> List[str]:
        if not self.camera_sources_raw:
            return []
        return [item.strip() for item in str(self.camera_sources_raw).split(",") if item.strip()]
