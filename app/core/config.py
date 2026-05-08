from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "MAJI - Analyse de Plans Techniques"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    max_image_size: int = 4096
    ocr_confidence_threshold: float = 0.7

    # Paramètres métier (modifiables via .env ou interface)
    default_margin_rate: float = 0.30
    machine_hourly_rate: float = 85.0
    operator_hourly_rate: float = 35.0

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
