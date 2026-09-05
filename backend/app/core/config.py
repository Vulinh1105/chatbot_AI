from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_v1_str: str = "/api/v1"
    project_name: str = "ThinkDocu"
    sqlalchemy_database_uri: str = "sqlite+aiosqlite:///./thinkdocu.db"
    secret_key: SecretStr = SecretStr("thinkdocu-super-secret-jwt-key-2026-very-secure-key-change-me")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 1 day
    admin_username: str = "admin"

    @property
    def async_database_uri(self) -> str:
        uri = self.sqlalchemy_database_uri
        if uri.startswith("postgresql://"):
            return uri.replace("postgresql://", "postgresql+asyncpg://", 1)
        if uri.startswith("postgres://"):
            return uri.replace("postgres://", "postgresql+asyncpg://", 1)
        if uri.startswith("sqlite://") and not uri.startswith("sqlite+aiosqlite://"):
            return uri.replace("sqlite://", "sqlite+aiosqlite://", 1)
        return uri


settings = Settings()
