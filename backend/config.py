
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # LLM provider: gemini, groq, or ollama
    llm_provider: str = "gemini"

    # Shared model configuration
    llm_model: str = "gemini-2.0-flash"

    # API keys
    google_api_key: str = ""
    groq_api_key: str = ""

    # Database configuration
    mongo_uri: str = "mongodb+srv://opsagent_user:opsagent_majorproject@cluster0.djhq5p4.mongodb.net/"
    mongo_db: str = "opsagent"

    # Simulated IT backend
    sim_backend_url: str = "http://localhost:8001"

    # Authentication
    jwt_secret_key: str = "opsagent_production_secure_jwt_secret_key_2026"
    jwt_access_token_expire_minutes: int = 60

    # Initial administrator account
    admin_username: str = "admin"
    admin_password: str = "admin_password_123"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


settings = Settings()
