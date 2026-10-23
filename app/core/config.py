from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Fitness Platform"
    API_V1_STR: str = "/api/v1"
    
    # Security
    SECRET_KEY: str = "dev_local_mock_token_for_testing_only"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/ai_fitness"

    # LLM Providers (Milestone 2)
    DEFAULT_LLM_PROVIDER: str = "groq"
    GROQ_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # Background Tasks & Cache (Milestone 3)
    REDIS_URL: str = "redis://localhost:6379/0"

    # Strava OAuth Integration (Milestone 3, Day 20)
    STRAVA_CLIENT_ID: str = ""
    STRAVA_CLIENT_SECRET: str = ""
    STRAVA_REDIRECT_URI: str = "http://localhost:8000/integrations/strava/callback"

    # ChromaDB Memory Store (Milestone 4, Day 22)
    CHROMA_PERSIST_DIR: str = "./chroma_data"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
