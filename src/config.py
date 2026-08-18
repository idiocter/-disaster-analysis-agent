from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = ""
    parser_model: str = "claude-sonnet-5"
    narrative_model: str = "claude-sonnet-5"

    gee_service_account_email: str = ""
    gee_service_account_json: str = ""

    database_url: str = ""
    boundary_source: str = "gadm"

    embedding_provider: str = "voyage"
    voyage_api_key: str = ""

    data_cache_dir: str = "data/cache"
    outputs_dir: str = "outputs"


settings = Settings()
