from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="PCM_",
        extra="ignore",
    )

    app_name: str = "Product Catalog Matcher"
    environment: Literal["development", "test", "production"] = "development"
    database_url: str = "postgresql+psycopg://catalog:catalog@localhost:5432/catalog"
    log_format: Literal["console", "json"] = "json"
    upload_max_bytes: int = Field(default=5 * 1024 * 1024, ge=1024)
    import_max_rows: int = Field(default=5_000, ge=1, le=100_000)
    auto_match_threshold: float = Field(default=0.88, ge=0.0, le=1.0)
    review_threshold: float = Field(default=0.65, ge=0.0, le=1.0)
    minimum_winning_margin: float = Field(default=0.08, ge=0.0, le=1.0)
    candidate_similarity_floor: float = Field(default=0.25, ge=0.0, le=1.0)
    candidate_limit: int = Field(default=20, ge=1, le=200)
    proposal_limit: int = Field(default=3, ge=1, le=20)
    semantic_matching_enabled: bool = False
    semantic_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    @model_validator(mode="after")
    def validate_matching_thresholds(self) -> "Settings":
        if self.review_threshold >= self.auto_match_threshold:
            msg = "review threshold must be lower than the automatic-match threshold"
            raise ValueError(msg)
        if self.proposal_limit > self.candidate_limit:
            msg = "proposal limit cannot exceed the candidate limit"
            raise ValueError(msg)
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
