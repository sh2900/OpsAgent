from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    google_api_key: str = ""
    llm_model: str = "gemini-3.8-flash"
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "opsagent"
    sim_backend_url: str = "http://localhost:8001"

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()