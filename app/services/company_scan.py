from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from app.models import AuditEvent, ScanRun
from app.models.enums import ActorType, CompanyStatus, ScanRunStatus, ScanType
from app.repositories.audit_repository import AuditRepository
from app.repositories.company_repository import CompanyRepository
from app.repositories.job_repository import JobRepository
from app.scanners.ats.greenhouse import GreenhouseAdapter, SourceScanError
from app.schemas.jobs import CompanyScanResult
from app.services.job_ingestion import JobIngestionService


class CompanyScanError(ValueError):
    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message


class CompanyScanService:
    """Synchronous manual scan boundary. Batch and scheduled scans move to Temporal next phase."""

    def __init__(
        self,
        company_repo: CompanyRepository,
        job_repo: JobRepository,
        audit_repo: AuditRepository,
    ) -> None:
        self.company_repo = company_repo
        self.job_repo = job_repo
        self.audit_repo = audit_repo
        self.ingestion = JobIngestionService(job_repo)

    def scan_company_greenhouse(self, company_id: int) -> CompanyScanResult:
        company = self.company_repo.get(company_id)
        if not company:
            raise CompanyScanError("missing_company", "Company not found.")
        if company.status != CompanyStatus.ACTIVE:
            raise CompanyScanError(
                "company_not_scan_eligible",
                "Only active companies can be scanned.",
            )
        adapter = GreenhouseAdapter()
        validation = asyncio.run(adapter.validate_company_source(company))
        if not validation.valid:
            scan_run = self._create_scan_run(
                company_id, validation.error_code or "unsupported_provider"
            )
            scan_run.status = ScanRunStatus.UNSUPPORTED
            scan_run.completed_at = datetime.now(UTC)
            scan_run.error_code = validation.error_code
            scan_run.error_message = validation.error_message
            self._record_company_scan_audit(company.id, scan_run)
            self.company_repo.session.commit()
            raise CompanyScanError(
                validation.error_code or "unsupported_provider",
                validation.error_message or "Unsupported company scan configuration.",
            )

        scan_run = self._create_scan_run(company.id, None)
        scan_run.status = ScanRunStatus.RUNNING
        scan_run.started_at = datetime.now(UTC)
        scan_run.source_provider = adapter.provider_name
        scan_run.request_metadata_json = {
            "mode": "manual_sync",
            "todo": "Move scan execution behind Temporal activities in Phase 4.",
            "board_url": validation.board_url,
        }
        self.company_repo.session.flush()

        try:
            raw_jobs = asyncio.run(adapter.discover_jobs(company))
            normalized_jobs = [
                self.ingestion.normalize_job(job, source_provider=adapter.provider_name)
                for job in raw_jobs
            ]
            ingestion_result = self.ingestion.ingest_company_jobs(
                company=company,
                normalized_jobs=normalized_jobs,
                scan_run=scan_run,
                authoritative=validation.authoritative,
            )
            company.last_scanned_at = datetime.now(UTC)
            scan_run.status = (
                ScanRunStatus.COMPLETED
                if not ingestion_result.warnings
                else ScanRunStatus.COMPLETED_WITH_WARNINGS
            )
            scan_run.completed_at = datetime.now(UTC)
            scan_run.jobs_discovered_count = ingestion_result.discovered_count
            scan_run.jobs_created_count = ingestion_result.created_count
            scan_run.jobs_updated_count = ingestion_result.updated_count
            scan_run.jobs_marked_removed_count = ingestion_result.marked_removed_count
            self._record_company_scan_audit(company.id, scan_run)
            self.company_repo.session.commit()
            return CompanyScanResult(
                company_id=company.id,
                scan_run_id=scan_run.id,
                status=scan_run.status.value,
                source_provider=scan_run.source_provider,
                discovered_count=scan_run.jobs_discovered_count,
                created_count=scan_run.jobs_created_count,
                updated_count=scan_run.jobs_updated_count,
                marked_removed_count=scan_run.jobs_marked_removed_count,
                warnings=ingestion_result.warnings,
            )
        except SourceScanError as exc:
            scan_run.status = ScanRunStatus.FAILED
            scan_run.completed_at = datetime.now(UTC)
            scan_run.error_code = exc.error_code
            scan_run.error_message = exc.message
            self._record_company_scan_audit(company.id, scan_run)
            self.company_repo.session.commit()
            raise CompanyScanError(exc.error_code, exc.message) from exc

    def _create_scan_run(self, company_id: int, error_code: str | None) -> ScanRun:
        scan_run = self.job_repo.add_scan_run(
            ScanRun(
                company_id=company_id,
                scan_type=ScanType.MANUAL_GREENHOUSE,
                source_provider="greenhouse",
                status=ScanRunStatus.PENDING,
                error_code=error_code,
            )
        )
        return scan_run

    def _record_company_scan_audit(self, company_id: int, scan_run: ScanRun) -> None:
        self.audit_repo.add(
            AuditEvent(
                event_type="company_greenhouse_scan",
                actor_type=ActorType.SYSTEM,
                entity_type="company_scan",
                entity_id=str(company_id),
                company_id=company_id,
                before_payload=None,
                after_payload={
                    "scan_run_id": scan_run.id,
                    "status": scan_run.status.value,
                    "jobs_discovered_count": scan_run.jobs_discovered_count,
                    "jobs_created_count": scan_run.jobs_created_count,
                    "jobs_updated_count": scan_run.jobs_updated_count,
                    "jobs_marked_removed_count": scan_run.jobs_marked_removed_count,
                    "error_code": scan_run.error_code,
                    "error_message": scan_run.error_message,
                },
                reason="Manual Greenhouse company scan.",
            )
        )
