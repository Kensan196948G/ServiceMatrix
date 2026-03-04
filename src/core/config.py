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

    # データベース（デフォルトはSQLite、PostgreSQL環境変数が揃えばPostgreSQLを使用）
    database_url: str = "sqlite+aiosqlite:///./servicematrix.db"

    # PostgreSQL個別設定（環境変数で指定時にdatabase_urlを上書き）
    postgres_host: str = ""
    postgres_port: int = 5432
    postgres_db: str = "servicematrix"
    postgres_user: str = "servicematrix"
    postgres_password: str = ""  # noqa: S105

    def get_database_url(self) -> str:
        """環境に応じたデータベースURLを返す。

        DATABASE_URLが明示的にpostgresqlで始まる場合はそのまま返す。
        POSTGRES_HOSTが設定されている場合はPostgreSQL URLを組み立てる。
        それ以外はデフォルトのSQLiteを返す。
        """
        if self.database_url.startswith("postgresql"):
            return self.database_url
        if self.postgres_host:
            return (
                f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
                f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
            )
        return self.database_url

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

    # LLM設定
    llm_provider: str = "keyword"  # "keyword" | "openai" | "azure_openai" | "ollama"
    llm_model: str = "gpt-4o-mini"
    openai_api_key: str = ""  # noqa: S105
    openai_api_base: str = ""  # Azure OpenAIのエンドポイントまたはOllamaのURL

    # アラート・通知設定
    github_token: str = ""  # noqa: S105
    github_repo: str = ""
    alert_webhook_url: str = ""
    alert_webhook_enabled: bool = False

    # SLAエンジン設定
    sla_check_interval_seconds: int = 60
    sla_warning_threshold_70: float = 0.70
    sla_warning_threshold_90: float = 0.90


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
