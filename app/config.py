from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str

    llm_provider: str = "anthropic"
    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    openai_api_key: str = ""

    adzuna_app_id: str = ""
    adzuna_app_key: str = ""
    jsearch_rapidapi_key: str = ""

    base_country: str = "MA"

    linkedin_session_cookie: str = ""
    scraper_min_delay_seconds: int = 5
    scraper_max_delay_seconds: int = 12


settings = Settings()
