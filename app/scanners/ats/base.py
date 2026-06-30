from __future__ import annotations

from typing import Protocol

from app.models.company import Company
from app.schemas.jobs import RawJobPosting, SourceValidationResult


class JobSourceAdapter(Protocol):
    provider_name: str

    def can_handle(self, company: Company) -> bool: ...

    async def discover_jobs(self, company: Company) -> list[RawJobPosting]: ...

    async def validate_company_source(self, company: Company) -> SourceValidationResult: ...
