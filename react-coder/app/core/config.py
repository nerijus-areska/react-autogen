from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "React Coder API"
    API_V1_STR: str = "/api/v1"

    SECRET_KEY: str = "secret"
    ALGORITHM: str = "HS256"

    # LLM Configuration
    LLM_BASE_URL: str = "http://localhost:1234/v1"
    LLM_API_KEY: str = "lm-studio"
    LLM_MODEL: str = "qwen3-coder-30b-a3b-instruct-mlx"
    LLM_MAX_TOKENS: int = 4096
    ROUTER_LLM_MODEL: str = ""  # if set, used for routing instead of LLM_MODEL

    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=True, extra="ignore"
    )


settings = Settings()
