from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Smart Hostel API"
    app_env: str = "development"
    database_url: str = "sqlite:///./smart_hostel.db"
    secret_key: str = "development-only-secret-change-in-production-32chars"
    access_token_minutes: int = 480
    cors_origins: str = "http://localhost:5173"
    kiosk_api_key: str = "change-this-kiosk-key"
    student_initial_password: str = "MRBH@Student2026"
    biometric_encryption_key: str | None = None
    demo_mode: bool = False

    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

    @property
    def cors_list(self) -> list[str]:
        return [value.strip() for value in self.cors_origins.split(",") if value.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
