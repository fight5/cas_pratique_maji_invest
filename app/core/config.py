from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "MAJI - Analyse de Plans Techniques"

    # Provider IA — Gemini (gratuit) ou OpenAI (payant)
    # Mettre GEMINI_API_KEY pour utiliser Gemini Flash (recommandé)
    # Mettre OPENAI_API_KEY pour utiliser GPT-4o
    gemini_api_key: str = ""
    openai_api_key: str = ""

    # Rempli automatiquement selon le provider détecté
    ai_model: str = "gemini-2.0-flash"

    max_image_size: int = 4096
    ocr_confidence_threshold: float = 0.7

    # Paramètres métier (modifiables via .env ou interface)
    default_margin_rate: float = 0.30
    machine_hourly_rate: float = 85.0
    operator_hourly_rate: float = 35.0

    @property
    def active_api_key(self) -> str:
        return self.gemini_api_key or self.openai_api_key

    @property
    def active_model(self) -> str:
        if self.gemini_api_key:
            return "gemini-2.0-flash"
        return "gpt-4o"

    @property
    def active_base_url(self) -> str | None:
        if self.gemini_api_key:
            return "https://generativelanguage.googleapis.com/v1beta/openai/"
        return None

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
