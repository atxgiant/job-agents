from __future__ import annotations

from datetime import UTC, datetime

from app.models import JobPosting, JobScanObservation, JobStatusHistory, ScanRun
from app.models.company import Company
from app.models.enums import ActorType, CareerSiteStatus, ReviewStatus
from app.repositories.job_repository import JobRepository
from app.schemas.jobs import JobIngestionResult, NormalizedJobPosting, RawJobPosting
from app.utils.job_text import (
    clean_url,
    normalize_location,
    normalize_text,
    normalize_title,
    stable_hash,
)


class JobIngestionService:
    def __init__(self, repository: JobRepository) -> None:
        self.repository = repository

    def normalize_job(
        self, raw_job: RawJobPosting, *, source_provider: str
    ) -> NormalizedJobPosting:
        description_text = normalize_text(raw_job.description_text)
        canonical_url = clean_url(raw_job.canonical_url or raw_job.source_url)
        application_url = clean_url(raw_job.application_url or canonical_url)
        return NormalizedJobPosting(
            external_job_id=raw_job.external_job_id,
            source_provider=source_provider,
            source_url=clean_url(raw_job.source_url) or raw_job.source_url,
            canonical_url=canonical_url,
            application_url=application_url,
            title=normalize_text(raw_job.title) or raw_job.title,
            normalized_title=normalize_title(raw_job.title),
            location=normalize_text(raw_job.location),
            normalized_location=normalize_location(raw_job.location),
            department=normalize_text(raw_job.department),
            employment_type=normalize_text(raw_job.employment_type),
            work_arrangement=None,
            posted_at=raw_job.posted_at,
            description_text=description_text,
            description_hash=stable_hash(description_text),
            salary_text=normalize_text(raw_job.salary_text),
            provider_metadata=raw_job.provider_metadata,
            source_payload_hash=stable_hash(str(raw_job.provider_metadata)),
        )

    def ingest_company_jobs(
        self,
        *,
        company: Company,
        normalized_jobs: list[NormalizedJobPosting],
        scan_run: ScanRun,
        authoritative: bool,
    ) -> JobIngestionResult:
        now = datetime.now(UTC)
        result = JobIngestionResult(
            discovered_count=len(normalized_jobs), authoritative=authoritative
        )
        seen_ids: set[int] = set()

        for normalized_job in normalized_jobs:
            existing = self.repository.find_existing_job(
                company_id=company.id,
                source_provider=normalized_job.source_provider,
                external_job_id=normalized_job.external_job_id,
                canonical_url=normalized_job.canonical_url,
                normalized_title=normalized_job.normalized_title,
                normalized_location=normalized_job.normalized_location,
                department=normalized_job.department,
            )
            if existing:
                changed = self.update_job_from_source(existing, normalized_job, observed_at=now)
                self.record_scan_observation(existing, scan_run, normalized_job, observed_at=now)
                seen_ids.add(existing.id)
                if changed:
                    result.updated_count += 1
                continue

            created = self.create_job(company, normalized_job, observed_at=now)
            self.record_scan_observation(created, scan_run, normalized_job, observed_at=now)
            self.repository.add_status_history(
                JobStatusHistory(
                    job_posting_id=created.id,
                    event_type="job_discovered",
                    actor_type=ActorType.SYSTEM,
                    previous_review_status=None,
                    new_review_status=ReviewStatus.NOT_REVIEWED,
                    previous_career_site_status=None,
                    new_career_site_status=CareerSiteStatus.ACTIVE,
                    reason="Discovered from official Greenhouse source.",
                    metadata_json={"scan_run_id": scan_run.id},
                )
            )
            seen_ids.add(created.id)
            result.created_count += 1

        if authoritative:
            result.marked_removed_count = self.mark_missing_jobs_removed(
                company_id=company.id,
                source_provider=scan_run.source_provider or "",
                seen_job_ids=seen_ids,
                observed_at=now,
            )
        return result

    def create_job(
        self,
        company: Company,
        normalized_job: NormalizedJobPosting,
        *,
        observed_at: datetime,
    ) -> JobPosting:
        job = JobPosting(
            company_id=company.id,
            external_job_id=normalized_job.external_job_id,
            source_provider=normalized_job.source_provider,
            source_url=normalized_job.source_url,
            canonical_url=normalized_job.canonical_url,
            application_url=normalized_job.application_url,
            title=normalized_job.title,
            normalized_title=normalized_job.normalized_title,
            location=normalized_job.location,
            normalized_location=normalized_job.normalized_location,
            department=normalized_job.department,
            employment_type=normalized_job.employment_type,
            work_arrangement=normalized_job.work_arrangement,
            salary_text=normalized_job.salary_text,
            posted_at=normalized_job.posted_at,
            first_seen_at=observed_at,
            last_seen_at=observed_at,
            last_verified_at=observed_at,
            career_site_status=CareerSiteStatus.ACTIVE,
            career_site_status_changed_at=observed_at,
            job_description_text=normalized_job.description_text,
            job_description_hash=normalized_job.description_hash,
            job_summary=None,
            review_status=ReviewStatus.NOT_REVIEWED,
            provider_metadata_json=normalized_job.provider_metadata,
        )
        return self.repository.add(job)

    def update_job_from_source(
        self,
        job: JobPosting,
        normalized_job: NormalizedJobPosting,
        *,
        observed_at: datetime,
    ) -> bool:
        previous_career_status = job.career_site_status
        changed = False
        fields = [
            ("source_url", normalized_job.source_url),
            ("canonical_url", normalized_job.canonical_url),
            ("application_url", normalized_job.application_url),
            ("title", normalized_job.title),
            ("normalized_title", normalized_job.normalized_title),
            ("location", normalized_job.location),
            ("normalized_location", normalized_job.normalized_location),
            ("department", normalized_job.department),
            ("employment_type", normalized_job.employment_type),
            ("salary_text", normalized_job.salary_text),
            ("posted_at", normalized_job.posted_at),
            ("job_description_text", normalized_job.description_text),
            ("job_description_hash", normalized_job.description_hash),
            ("provider_metadata_json", normalized_job.provider_metadata),
        ]
        for field_name, new_value in fields:
            if getattr(job, field_name) != new_value:
                setattr(job, field_name, new_value)
                changed = True

        job.last_seen_at = observed_at
        job.last_verified_at = observed_at
        if job.career_site_status != CareerSiteStatus.ACTIVE:
            job.career_site_status = CareerSiteStatus.ACTIVE
            job.career_site_status_changed_at = observed_at
            changed = True
            self.repository.add_status_history(
                JobStatusHistory(
                    job_posting_id=job.id,
                    event_type="career_site_status_changed",
                    actor_type=ActorType.SYSTEM,
                    previous_review_status=None,
                    new_review_status=None,
                    previous_career_site_status=previous_career_status,
                    new_career_site_status=CareerSiteStatus.ACTIVE,
                    reason="Job reappeared in an authoritative source scan.",
                    metadata_json={},
                )
            )
        return changed

    def mark_missing_jobs_removed(
        self,
        *,
        company_id: int,
        source_provider: str,
        seen_job_ids: set[int],
        observed_at: datetime,
    ) -> int:
        removed_count = 0
        active_jobs = self.repository.list_active_jobs_for_company(company_id, source_provider)
        for job in active_jobs:
            if job.id in seen_job_ids:
                continue
            previous_status = job.career_site_status
            job.career_site_status = CareerSiteStatus.REMOVED
            job.career_site_status_changed_at = observed_at
            job.last_verified_at = observed_at
            removed_count += 1
            self.repository.add_status_history(
                JobStatusHistory(
                    job_posting_id=job.id,
                    event_type="career_site_status_changed",
                    actor_type=ActorType.SYSTEM,
                    previous_review_status=None,
                    new_review_status=None,
                    previous_career_site_status=previous_status,
                    new_career_site_status=CareerSiteStatus.REMOVED,
                    reason="Job missing from authoritative source scan.",
                    metadata_json={},
                )
            )
        return removed_count

    def record_scan_observation(
        self,
        job: JobPosting,
        scan_run: ScanRun,
        normalized_job: NormalizedJobPosting,
        *,
        observed_at: datetime,
    ) -> JobScanObservation:
        return self.repository.add_observation(
            JobScanObservation(
                job_posting_id=job.id,
                scan_run_id=scan_run.id,
                observed_status=job.career_site_status,
                source_payload_hash=normalized_job.source_payload_hash,
                title_snapshot=job.title,
                location_snapshot=job.location,
                department_snapshot=job.department,
                description_hash_snapshot=job.job_description_hash,
                observed_at=observed_at,
            )
        )
