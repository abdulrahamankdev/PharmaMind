"""
PharmaMind MVP — Configuration
Loads environment variables and exposes typed settings via Pydantic.
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    # ── Neo4j ──────────────────────────────────────────────────────────────
    neo4j_uri: str = Field(default="bolt://localhost:7687", alias="NEO4J_URI")
    neo4j_user: str = Field(default="neo4j", alias="NEO4J_USER")
    neo4j_password: str = Field(default="pharma123", alias="NEO4J_PASSWORD")

    # ── Ollama ─────────────────────────────────────────────────────────────
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="llama3", alias="OLLAMA_MODEL")

    # ── External APIs ──────────────────────────────────────────────────────
    chembl_api_base: str = Field(
        default="https://www.ebi.ac.uk/chembl/api/data",
        alias="CHEMBL_API_BASE",
    )
    pubmed_api_base: str = Field(
        default="https://eutils.ncbi.nlm.nih.gov/entrez/eutils",
        alias="PUBMED_API_BASE",
    )
    pubmed_email: str = Field(default="researcher@pharmamind.ai", alias="PUBMED_EMAIL")

    # ── FastAPI ────────────────────────────────────────────────────────────
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    cors_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:5500",
        alias="CORS_ORIGINS",
    )

    # ── Scoring Thresholds ─────────────────────────────────────────────────
    selectivity_score_threshold: float = Field(
        default=0.7, alias="SELECTIVITY_SCORE_THRESHOLD"
    )
    ooc_flag_mw_max: float = Field(default=500.0, alias="OOC_FLAG_MW_MAX")
    ic50_activity_threshold_nm: float = Field(
        default=1000.0, alias="IC50_ACTIVITY_THRESHOLD_NM"
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    model_config = {"env_file": ".env", "populate_by_name": True}


@lru_cache
def get_settings() -> Settings:
    return Settings()
