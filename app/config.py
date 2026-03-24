"""Application configuration managed via environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "metadata_inventory"
    request_timeout: float = 10.0

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
