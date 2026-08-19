from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str = ""
    # Override in .env to whatever your account has access to -- nothing in
    # the code depends on these specific model names.
    parser_model: str = "gpt-4o-mini"
    narrative_model: str = "gpt-4o"

    gee_service_account_email: str = ""
    gee_service_account_json: str = ""

    database_url: str = ""
    boundary_source: str = "gadm"

    embedding_provider: str = "voyage"
    voyage_api_key: str = ""

    data_cache_dir: str = "data/cache"
    outputs_dir: str = "outputs"


settings = Settings()
