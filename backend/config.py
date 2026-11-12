
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # LLM provider: gemini, groq, or ollama
    llm_provider: str = "gemini"

    # Shared model configuration
    llm_model: str = "gemini-3.8-flash"

    # API keys
    google_api_key: str = ""
    groq_api_key: str = ""

    # Database configuration
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "opsagent"

    # Simulated IT backend
    sim_backend_url: str = "http://localhost:8001"

    # Authentication
    jwt_secret_key: str = ""
    jwt_access_token_expire_minutes: int = 60

    # Initial administrator account
    admin_username: str = ""
    admin_password: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


settings = Settings()
