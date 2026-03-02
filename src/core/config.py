"""アプリケーション設定 - Pydantic Settings"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # アプリ基本設定
    app_name: str = "ServiceMatrix"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"

    # データベース
    database_url: str = "postgresql+asyncpg://servicematrix:password@localhost:5432/servicematrix"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT認証
    secret_key: str = "change-this-in-production"  # noqa: S105
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    jwt_algorithm: str = "HS256"

    # CORS
    allowed_origins: list[str] = ["http://localhost:3000", "http://localhost:8000"]

    # 監査ログ
    audit_log_retention_years: int = 7

    # GitHub Webhook
    github_webhook_secret: str = ""

    # アラート・通知設定
    github_token: str = ""  # noqa: S105
    github_repo: str = ""
    alert_webhook_url: str = ""
    alert_webhook_enabled: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
