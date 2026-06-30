from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ScanRetryPolicy(BaseModel):
    maximum_attempts: int = 3
    initial_interval_seconds: int = 30
    maximum_interval_seconds: int = 600


class ScanPolicy(BaseModel):
    enabled: bool = True
    cadence: str = "daily"
    total_scan_blocks: int = 7
    scan_block_strategy: str = "rotating"
    companies_per_run_limit: int = 50
    per_company_timeout_seconds: int = 45
    retry_policy: ScanRetryPolicy = Field(default_factory=ScanRetryPolicy)
    respect_rate_limits: bool = True
    user_agent: str = "HeadHunter/0.1"
    revalidate_open_roles: dict[str, Any] = Field(
        default_factory=lambda: {"enabled": True, "cadence": "weekly"}
    )


class SeedPolicy(BaseModel):
    enabled: bool = True
    provider: str = "openai"
    model: str = "gpt-4.1-mini"
    interval_days: int = 30
    seed_prompt: str = "Identify companies that fit the target company profile."
    reference_universe: dict[str, Any] = Field(default_factory=dict)
    inclusion_criteria: list[str] = Field(default_factory=list)
    exclusion_criteria: list[str] = Field(default_factory=list)
    automatic_activation: bool = True
    max_candidates_per_run: int = 100
    max_llm_budget_usd_per_run: float = 10.0


class ScoreWeights(BaseModel):
    fit: float = 0.45
    competitiveness: float = 0.30
    interest: float = 0.20
    recency: float = 0.05


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    head_hunter_env: str = "development"
    database_url: str = "sqlite:///data/head_hunter.db"
    temporal_address: str = "localhost:7233"
    temporal_namespace: str = "default"
    temporal_task_queue: str = "head-hunter"
    llm_provider: str = "openai"
    openai_api_key: str = ""
    openai_base_url: str = ""
    openai_model: str = ""
    openai_monthly_budget_usd: float = 25.0
    flask_secret_key: str = "replace-me"
    log_level: str = "INFO"
    config_path: Path = Path("config/settings.example.yaml")
    seed_policy_path: Path = Path("config/seed-policy.example.yaml")
    scan_policy_path: Path = Path("config/scan-policy.example.yaml")


class RuntimeConfig(BaseModel):
    app_env: str = "development"
    host: str = "127.0.0.1"
    port: int = 5000
    flask_secret_key: str = "replace-me"
    database_url: str = "sqlite:///data/head_hunter.db"
    candidate_profile_path: str = "skillset.local.md"
    csv_export_directory: str = "data/exports"
    log_level: str = "INFO"
    temporal_namespace: str = "default"
    temporal_task_queue: str = "head-hunter"
    default_company_scan_timeout: int = 45
    exclusion_policy: dict[str, Any] = Field(default_factory=dict)
    feature_toggles: dict[str, bool] = Field(default_factory=dict)
    scan_policy: ScanPolicy = Field(default_factory=ScanPolicy)
    seed_policy: SeedPolicy = Field(default_factory=SeedPolicy)
    score_weights: ScoreWeights = Field(default_factory=ScoreWeights)


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {path}")
    return data


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    return AppSettings()


@lru_cache(maxsize=1)
def load_runtime_config() -> RuntimeConfig:
    settings = get_settings()
    base = _load_yaml(settings.config_path)
    base["database_url"] = settings.database_url
    base["flask_secret_key"] = settings.flask_secret_key
    base["log_level"] = settings.log_level
    base["temporal_namespace"] = settings.temporal_namespace
    base["temporal_task_queue"] = settings.temporal_task_queue

    if settings.scan_policy_path.exists():
        base["scan_policy"] = _load_yaml(settings.scan_policy_path).get("scan_policy", {})
    if settings.seed_policy_path.exists():
        base["seed_policy"] = _load_yaml(settings.seed_policy_path).get("seed_policy", {})

    return RuntimeConfig.model_validate(base)
