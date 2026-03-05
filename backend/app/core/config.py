from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "App Builder Local"
    DEBUG: bool = True

    # PostgreSQL
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/app_builder"

    # Encryption key for API tokens (AES-256)
    ENCRYPTION_KEY: str = ""

    # Agent settings
    MAX_CONCURRENT_AGENTS: int = 3
    PROJECT_ROOT: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
