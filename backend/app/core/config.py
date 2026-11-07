from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Pocket Fitter API"
    cors_origins: list[str] = ["http://localhost:5173"]

    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash"
    gemini_fallback_model: str = "gemini-2.5-flash"


settings = Settings()
