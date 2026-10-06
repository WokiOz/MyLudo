from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Paramètres lus depuis l'environnement ou le fichier .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:////data/myludo.db"
    static_dir: str = "/app/static"
    app_password: str = ""

    bgg_token: str = ""
    youtube_api_key: str = ""
    youtube_channels: str = "Ludochrono"
    anthropic_api_key: str = ""

    price_sources: str = ""
    price_refresh_cron: str = "0 3 * * *"

    @property
    def enabled_price_sources(self) -> list[str]:
        return [s.strip() for s in self.price_sources.split(",") if s.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
