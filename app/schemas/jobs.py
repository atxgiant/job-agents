from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RawJobPosting(BaseModel):
    external_job_id: str | None = None
    title: str
    location: str | None = None
    department: str | None = None
    office: str | None = None
    employment_type: str | None = None
    posted_at: datetime | None = None
    source_url: str
    canonical_url: str | None = None
    application_url: str | None = None
    description_html: str | None = None
    description_text: str | None = None
    salary_text: str | None = None
    provider_metadata: dict[str, Any] = Field(default_factory=dict)


class NormalizedJobPosting(BaseModel):
    external_job_id: str | None = None
    source_provider: str
    source_url: str
    canonical_url: str | None = None
    application_url: str | None = None
    title: str
    normalized_title: str
    location: str | None = None
    normalized_location: str | None = None
    department: str | None = None
    employment_type: str | None = None
    work_arrangement: str | None = None
    posted_at: datetime | None = None
    description_text: str | None = None
    description_hash: str | None = None
    salary_text: str | None = None
    provider_metadata: dict[str, Any] = Field(default_factory=dict)
    source_payload_hash: str | None = None


class SourceValidationResult(BaseModel):
    valid: bool
    authoritative: bool = False
    board_token: str | None = None
    board_url: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    warnings: list[str] = Field(default_factory=list)


class JobIngestionResult(BaseModel):
    discovered_count: int = 0
    created_count: int = 0
    updated_count: int = 0
    marked_removed_count: int = 0
    warnings: list[str] = Field(default_factory=list)
    authoritative: bool = False


class CompanyScanResult(BaseModel):
    company_id: int
    scan_run_id: int
    status: str
    source_provider: str | None = None
    discovered_count: int = 0
    created_count: int = 0
    updated_count: int = 0
    marked_removed_count: int = 0
    warnings: list[str] = Field(default_factory=list)
    error_code: str | None = None
    error_message: str | None = None
