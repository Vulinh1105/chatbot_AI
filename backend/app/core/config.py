from pathlib import Path
from pydantic import SecretStr, Field
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
    documents_dir: str = "./backend/documents"
    max_upload_size_bytes: int = Field(default=20 * 1024 * 1024, gt=0)

    # MinIO Storage Settings
    minio_endpoint: str = Field(default="188.245.107.192:9000", validation_alias="MINIO_ENDPOINT")
    minio_secure: bool = Field(default=False, validation_alias="MINIO_SECURE")
    minio_access_key: str = Field(default="minioadmin", validation_alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(default="minioadmin", validation_alias="MINIO_SECRET_KEY")
    minio_bucket_name: str = Field(default="documents", validation_alias="MINIO_BUCKET_NAME")
    minio_region: str = Field(default="us-east-1", validation_alias="MINIO_REGION")

    # Chunk & Upload limits
    upload_chunk_size_bytes: int = Field(default=10485760, validation_alias="UPLOAD_CHUNK_SIZE_BYTES")  # 10 MiB
    max_document_size_bytes: int = Field(default=5 * 1024 * 1024 * 1024, validation_alias="MAX_DOCUMENT_SIZE_BYTES")  # 5 GiB
    upload_session_ttl_seconds: int = Field(default=86400, validation_alias="UPLOAD_SESSION_TTL_SECONDS")  # 24 giờ
    upload_max_concurrency: int = Field(default=5, validation_alias="UPLOAD_MAX_CONCURRENCY")
    upload_max_sessions_per_user: int = Field(default=10, validation_alias="UPLOAD_MAX_SESSIONS_PER_USER")

    # Cache & Processing Dirs
    document_processing_temp_dir: str = Field(default="data/temp", validation_alias="DOCUMENT_PROCESSING_TEMP_DIR")

    # Indexing & Worker Settings
    index_job_max_attempts: int = Field(default=3, validation_alias="INDEX_JOB_MAX_ATTEMPTS")
    index_job_timeout_seconds: int = Field(default=1800, validation_alias="INDEX_JOB_TIMEOUT_SECONDS")

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

    @property
    def canonical_documents_dir(self) -> Path:
        """Đường dẫn tuyệt đối cho cache xử lý pipeline ingestion."""
        path = Path(self.documents_dir).resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def canonical_temp_dir(self) -> Path:
        """Đường dẫn tuyệt đối cho file tạm staging/download dở dang."""
        path = Path(self.document_processing_temp_dir).resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()