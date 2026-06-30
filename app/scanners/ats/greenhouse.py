from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

import httpx

from app.config.settings import load_runtime_config
from app.models.company import Company
from app.schemas.jobs import RawJobPosting, SourceValidationResult
from app.utils.job_text import clean_url, html_to_text


class SourceScanError(RuntimeError):
    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message


class GreenhouseAdapter:
    provider_name = "greenhouse"

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    def can_handle(self, company: Company) -> bool:
        provider = (company.ats_provider or "").strip().lower()
        return provider == self.provider_name

    async def validate_company_source(self, company: Company) -> SourceValidationResult:
        if not self.can_handle(company):
            return SourceValidationResult(
                valid=False,
                authoritative=False,
                error_code="unsupported_provider",
                error_message="Company is not configured with the Greenhouse provider.",
            )
        board_token = self._resolve_board_token(company)
        if not board_token:
            return SourceValidationResult(
                valid=False,
                authoritative=False,
                error_code="missing_ats_configuration",
                error_message=(
                    "Greenhouse scans require ats_company_identifier or "
                    "a valid Greenhouse board URL."
                ),
            )
        board_url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true"
        return SourceValidationResult(
            valid=True,
            authoritative=True,
            board_token=board_token,
            board_url=board_url,
        )

    async def discover_jobs(self, company: Company) -> list[RawJobPosting]:
        validation = await self.validate_company_source(company)
        if not validation.valid or not validation.board_url or not validation.board_token:
            raise SourceScanError(
                validation.error_code or "missing_ats_configuration",
                validation.error_message or "Greenhouse configuration is invalid.",
            )

        payload = await self._fetch_board(validation.board_url)
        jobs = payload.get("jobs")
        if not isinstance(jobs, list):
            raise SourceScanError("source_incomplete", "Greenhouse response did not contain jobs.")
        raw_jobs: list[RawJobPosting] = []
        for item in jobs:
            if not isinstance(item, dict):
                continue
            raw_jobs.append(self._build_raw_job(validation.board_token, item))
        return raw_jobs

    async def _fetch_board(self, url: str) -> dict[str, Any]:
        config = load_runtime_config()
        headers = {"User-Agent": config.scan_policy.user_agent, "Accept": "application/json"}
        timeout = httpx.Timeout(config.scan_policy.per_company_timeout_seconds)
        client = self._client or httpx.AsyncClient(
            timeout=timeout, headers=headers, follow_redirects=True
        )
        owns_client = self._client is None
        try:
            response = await client.get(url)
        except httpx.TimeoutException as exc:
            raise SourceScanError("source_timeout", "Greenhouse request timed out.") from exc
        except httpx.HTTPError as exc:
            raise SourceScanError(
                "source_unavailable", "Unable to reach Greenhouse board."
            ) from exc
        finally:
            if owns_client:
                await client.aclose()

        if response.status_code == 403:
            raise SourceScanError("source_access_denied", "Greenhouse board denied access.")
        if response.status_code == 429:
            raise SourceScanError(
                "source_rate_limited", "Greenhouse board rate limited the request."
            )
        if response.status_code >= 500:
            raise SourceScanError("source_unavailable", "Greenhouse board is unavailable.")
        if response.status_code >= 400:
            raise SourceScanError("invalid_source_url", "Greenhouse board URL is invalid.")

        try:
            return response.json()
        except ValueError as exc:
            raise SourceScanError(
                "source_parse_error", "Greenhouse response was not valid JSON."
            ) from exc

    def _resolve_board_token(self, company: Company) -> str | None:
        candidates = [
            company.ats_company_identifier,
            company.careers_url,
            company.source_urls,
        ]
        for candidate in candidates:
            token = self._extract_board_token(candidate)
            if token:
                return token
        return None

    def _extract_board_token(self, value: str | None) -> str | None:
        if not value:
            return None
        cleaned = value.strip()
        if re.fullmatch(r"[A-Za-z0-9_-]+", cleaned):
            return cleaned
        match = re.search(
            r"boards(?:-api)?\.greenhouse\.io/(?:embed/)?job_board(?:\?|/)|job-boards\.greenhouse\.io/([A-Za-z0-9_-]+)",
            cleaned,
        )
        if match and match.group(1):
            return match.group(1)
        parsed = urlparse(cleaned)
        if "boards.greenhouse.io" in parsed.netloc or "job-boards.greenhouse.io" in parsed.netloc:
            parts = [part for part in parsed.path.split("/") if part]
            if parts:
                return parts[0]
        return None

    def _build_raw_job(self, board_token: str, payload: dict[str, Any]) -> RawJobPosting:
        metadata = payload.get("metadata") or []
        department = None
        employment_type = None
        salary_text = None
        for item in metadata:
            if not isinstance(item, dict):
                continue
            name = (item.get("name") or "").lower()
            value = item.get("value")
            if not value:
                continue
            if name in {"department", "team"} and not department:
                department = str(value)
            if "employment" in name and not employment_type:
                employment_type = str(value)
            if "compensation" in name or "salary" in name:
                salary_text = str(value)

        absolute_url = payload.get("absolute_url") or payload.get("url")
        source_url = (
            clean_url(str(absolute_url))
            or f"https://job-boards.greenhouse.io/{board_token}/jobs/{payload.get('id')}"
        )
        content = payload.get("content")
        description_html = str(content) if content is not None else None
        description_text = html_to_text(description_html)
        location_data = payload.get("location") or {}
        location = location_data.get("name") if isinstance(location_data, dict) else None
        posted_at = None
        updated_at = payload.get("updated_at")
        if isinstance(updated_at, str):
            try:
                posted_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00")).astimezone(
                    UTC
                )
            except ValueError:
                posted_at = None
        return RawJobPosting(
            external_job_id=str(payload.get("id")) if payload.get("id") is not None else None,
            title=str(payload.get("title") or "Untitled role"),
            location=location,
            department=department,
            office=(location_data.get("name") if isinstance(location_data, dict) else None),
            employment_type=employment_type,
            posted_at=posted_at,
            source_url=source_url,
            canonical_url=source_url,
            application_url=source_url,
            description_html=description_html,
            description_text=description_text,
            salary_text=salary_text,
            provider_metadata={"raw": payload},
        )
