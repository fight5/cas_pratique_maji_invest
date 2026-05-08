import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


class Settings:
    def __init__(self):
        self.app_name = "MAJI - Analyse de Plans Techniques"
        self.gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
        self.openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
        self.max_image_size: int = int(os.getenv("MAX_IMAGE_SIZE", "4096"))
        self.ocr_confidence_threshold: float = float(os.getenv("OCR_CONFIDENCE_THRESHOLD", "0.7"))
        self.default_margin_rate: float = float(os.getenv("DEFAULT_MARGIN_RATE", "0.30"))
        self.machine_hourly_rate: float = float(os.getenv("MACHINE_HOURLY_RATE", "85.0"))
        self.operator_hourly_rate: float = float(os.getenv("OPERATOR_HOURLY_RATE", "35.0"))

    @property
    def active_api_key(self) -> str:
        return self.gemini_api_key or self.openai_api_key

    @property
    def active_model(self) -> str:
        return "gemini-2.5-flash" if self.gemini_api_key else "gpt-4o"

    @property
    def active_base_url(self):
        if self.gemini_api_key:
            return "https://generativelanguage.googleapis.com/v1beta/openai/"
        return None


@lru_cache()
def get_settings() -> Settings:
    return Settings()
