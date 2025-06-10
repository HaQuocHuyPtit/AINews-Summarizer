from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "ainsight"
    postgres_user: str = "ainsight"
    postgres_password: str = "changeme"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"

    # SMTP
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_from: str = "ainsight@yourcompany.com"
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = False

    # Scheduler
    schedule_hour: int = 7
    schedule_minute: int = 0

    # Langfuse
    langfuse_enabled: bool = False
    langfuse_host: str = "http://localhost:3000"
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Paper search
    arxiv_max_results: int = 20
    semantic_scholar_max_results: int = 10


settings = Settings()
