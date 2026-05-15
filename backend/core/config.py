from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_name: str = "JARVIS"
    app_env: str = "development"
    debug: bool = True
    secret_key: str = "change-me"
    allowed_origins: list[str] = ["http://localhost:3000"]

    # JWT
    jwt_secret_key: str = "change-me-jwt"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # PostgreSQL
    database_url: str = "postgresql+asyncpg://jarvis:jarvis_secret@postgres:5432/jarvis_db"
    alembic_database_url: str = "postgresql://jarvis:jarvis_secret@postgres:5432/jarvis_db"

    # Redis
    redis_url: str = "redis://:redis_secret@redis:6379/0"

    # Claude (Anthropic)
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-6"
    claude_max_tokens: int = 8192

    # Gemini
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    # Groq
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    # OpenAI (embedding uniquement)
    openai_api_key: str = ""

    @property
    def openai_key_valid(self) -> bool:
        return bool(self.openai_api_key) and "REMPLACE" not in self.openai_api_key and len(self.openai_api_key) > 20

    # Recherche web
    serpapi_key: str = ""
    tavily_key: str = ""

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""

    # Spotify OAuth
    spotify_client_id: str = ""
    spotify_client_secret: str = ""

    # Chiffrement OAuth tokens
    encryption_key: str = ""

    # Ollama
    ollama_enabled: bool = True
    ollama_base_url: str = "http://ollama:11434"
    ollama_default_model: str = "llama3.2"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
