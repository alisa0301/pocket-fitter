from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Pocket Fitter API"
    cors_origins: list[str] = ["http://localhost:5173"]

    static_dir: str = ""  # path to frontend/dist; set in the Docker image

    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash"
    gemini_fallback_model: str = "gemini-3.8-flash"

    mongodb_uri: str = ""  # empty -> catalog from bundled JSON, fittings not saved
    mongodb_db: str = "pocket_fitter"

    # Final club decision: auto (gemini if key set, else rules) | gemini | rules | jeff
    decision_engine: str = "auto"
    jeff_url: str = ""

    @field_validator("gemini_api_key", "gemini_model", "gemini_fallback_model", "mongodb_uri")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()


settings = Settings()
