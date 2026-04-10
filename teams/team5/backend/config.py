"""Application settings loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ANTHROPIC_API_KEY: str = ""
    LLM_PROVIDER: str = "anthropic"
    LLM_MODEL: str = "claude-sonnet-4-20250514"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    EMBEDDING_MODEL: str = "multilingual-e5-large"
    CHROMADB_PATH: str = "data/chromadb"
    FEEDBACK_DB_PATH: str = "data/feedback.db"
    KANKER_NL_JSON_PATH: str = "data/kanker_nl_pages_all.json"
    PUBLICATIONS_DIR: str = "data/reports"
    SCIENTIFIC_PUBLICATIONS_DIR: str = "data/scientific_publications"
    SITEMAP_PATH: str = "data/sitemap.json"
    NKR_API_BASE_URL: str = "https://api.nkr-cijfers.iknl.nl/api"
    CANCER_ATLAS_URL: str = "https://kankeratlas.iknl.nl"
    CANCER_ATLAS_STRAPI_URL: str = "https://iknl-atlas-strapi-prod.azurewebsites.net"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
