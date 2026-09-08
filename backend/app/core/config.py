"""Runtime configuration — read once from environment / .env file."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_env: str = "dev"  # dev | prod | test

    database_url: str = "sqlite:///./app.db"

    jwt_secret: str = "dev-only-change-me"
    jwt_expires_days: int = 7

    admin_email: str = "admin@example.com"
    admin_password: str = ""  # blank -> admin seed is skipped

    groq_api_key: str = ""
    groq_model: str = "qwen/qwen3.8-27b"
    groq_max_per_min: int = 25
    groq_max_per_day: int = 1000

    google_service_account_file: str = "./secrets/gsa.json"
    google_sheet_id: str = ""

    timezone: str = "Asia/Kolkata"

    cors_origins: str = "*"

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_pass: str = ""
    smtp_from: str = ""

    # --- derived -----------------------------------------------------------
    @property
    def is_prod(self) -> bool:
        return self.app_env.lower() == "prod"

    @property
    def is_test(self) -> bool:
        return self.app_env.lower() == "test"

    @property
    def cors_origin_list(self) -> list[str]:
        items = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        return items or ["*"]

    @property
    def groq_mock_mode(self) -> bool:
        return not self.groq_api_key

    def startup_warnings(self) -> list[str]:
        """Non-fatal config problems worth logging at boot."""
        warns: list[str] = []
        if self.is_prod and self.jwt_secret == "dev-only-change-me":
            warns.append("JWT_SECRET is still the default value in prod.")
        if self.is_prod and len(self.jwt_secret.encode()) < 32:
            warns.append("JWT_SECRET is shorter than 32 bytes — use a longer random string.")
        if not self.admin_password:
            warns.append("ADMIN_PASSWORD is blank — admin seed will be skipped.")
        if self.is_prod and "*" in self.cors_origin_list:
            warns.append("CORS_ORIGINS is '*' in prod — lock it to the frontend URL.")
        return warns


@lru_cache
def get_settings() -> Settings:
    return Settings()
