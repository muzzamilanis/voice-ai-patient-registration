"""Runtime configuration loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All secrets and tunables live here so nothing is hardcoded in source."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Voice AI Patient Registration"
    app_env: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    public_base_url: str = "http://localhost:8000"

    database_url: str = "sqlite:///./data/patients.db"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    vapi_webhook_secret: str = ""
    voice_api_token: str = ""


settings = Settings()
