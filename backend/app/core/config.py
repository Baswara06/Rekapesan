"""Konfigurasi aplikasi. Semua nilai dibaca dari `.env` di akar repo (lihat `.env.example`)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    database_url: str = "sqlite:///./rekapesan.db"

    llm_provider: str = "openrouter"
    llm_base_url: str = "https://openrouter.ai/api/v1"
    llm_api_key: str = ""
    llm_model: str = ""

    llm_fallback_base_url: str = ""
    llm_fallback_api_key: str = ""
    llm_fallback_model: str = ""

    vision_model: str = ""

    app_secret_key: str = "ganti-dengan-string-acak-panjang"
    demo_username: str = "demo"
    demo_password: str = ""
    jumlah_tidak_wajar_default: int = 20
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
