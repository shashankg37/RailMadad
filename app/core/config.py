from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "sqlite://"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret_key: str = "development-only-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    cloudinary_cloud_name: str = ""
    cloudinary_api_key: str = ""
    cloudinary_api_secret: str = ""
    qwen_api_key: str = ""
    qwen_base_url: str = ""
    qwen_model: str = "Qwen/Qwen3.8-27B"
    qwen_provider: str = ""
    sarvam_api_key: str = ""
    sarvam_base_url: str = "https://api.sarvam.ai"
    sarvam_model: str = "saaras:v3"
    yolo_model_path: Path = Path.home() / "railmadad-models" / "best.pt"
    yolo_confidence_threshold: float = 0.5
    video_max_frames: int = 8
    video_sample_interval_seconds: int = 2
    external_timeout_seconds: float = 30
    max_upload_size_mb: int = 25
    allowed_image_types: str = "image/jpeg,image/png,image/webp"
    allowed_video_types: str = "video/mp4,video/webm"
    allowed_audio_types: str = "audio/mpeg,audio/wav,audio/ogg,audio/mp4"
    local_storage_path: Path = Path.home() / "railmadad-storage"

    @property
    def allowed_types(self) -> set[str]:
        return set((self.allowed_image_types + "," + self.allowed_video_types + "," + self.allowed_audio_types).split(","))


@lru_cache
def get_settings() -> Settings:
    return Settings()
