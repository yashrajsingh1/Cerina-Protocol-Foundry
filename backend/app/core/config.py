from functools import lru_cache
from pydantic import Field

# pydantic v2 split settings into a separate package `pydantic-settings` in some
# environments. Try importing from there first for compatibility, otherwise
# fall back to the compatibility export on `pydantic` so the app can start in
# environments where `pydantic_settings` isn't available.
try:
    from pydantic_settings import BaseSettings  # type: ignore
except Exception:
    from pydantic import BaseSettings  # type: ignore


class Settings(BaseSettings):
    app_name: str = "Cerina Protocol Foundry Backend"
    api_prefix: str = "/api"
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    # SQLite files
    app_db_url: str = Field(
        default="sqlite+aiosqlite:///./cerina_app.db", env="CERINA_APP_DB_URL"
    )
    checkpoint_db_path: str = Field(
        default="cerina_checkpoints.db", env="CERINA_CHECKPOINT_DB_PATH"
    )

    # LLM configuration (Anthropic by default)
    anthropic_api_key: str | None = Field(default=None, env="ANTHROPIC_API_KEY")
    model_name: str = Field(default="claude-3-5-sonnet-20240620", env="CERINA_MODEL_NAME")

    # CORS
    frontend_origin: str = Field(default="http://localhost:5173", env="CERINA_FRONTEND_ORIGIN")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
