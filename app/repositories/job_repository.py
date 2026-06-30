from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Select, select
from sqlalchemy.orm import Session, joinedload

from app.models import JobPosting, JobScanObservation, JobStatusHistory, ScanRun
from app.models.enums import CareerSiteStatus, ReviewStatus


@dataclass(slots=True)
class OpportunityFilters:
    company_id: str = ""
    review_status: str = ""
    career_site_status: str = ""
    location: str = ""
    department: str = ""
    source_provider: str = ""
    first_seen_from: str = ""
    first_seen_to: str = ""
    last_verified_from: str = ""
    last_verified_to: str = ""
    active_view: str = "queue"


class JobRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, job: JobPosting) -> JobPosting:
        self.session.add(job)
        self.session.flush()
        return job

    def add_observation(self, observation: JobScanObservation) -> JobScanObservation:
        self.session.add(observation)
        self.session.flush()
        return observation

    def add_status_history(self, history: JobStatusHistory) -> JobStatusHistory:
        self.session.add(history)
        self.session.flush()
        return history

    def add_scan_run(self, scan_run: ScanRun) -> ScanRun:
        self.session.add(scan_run)
        self.session.flush()
        return scan_run

    def get_job(self, job_id: int) -> JobPosting | None:
        stmt = (
            select(JobPosting)
            .options(joinedload(JobPosting.company))
            .where(JobPosting.id == job_id)
        )
        return self.session.scalars(stmt).first()

    def get_scan_run(self, scan_run_id: int) -> ScanRun | None:
        return self.session.get(ScanRun, scan_run_id)

    def list_company_jobs(self, company_id: int) -> list[JobPosting]:
        stmt = (
            select(JobPosting)
            .options(joinedload(JobPosting.company))
            .where(JobPosting.company_id == company_id)
            .order_by(JobPosting.first_seen_at.desc(), JobPosting.title.asc())
        )
        return list(self.session.scalars(stmt).all())

    def list_scan_runs_for_company(self, company_id: int) -> list[ScanRun]:
        stmt = (
            select(ScanRun)
            .where(ScanRun.company_id == company_id)
            .order_by(ScanRun.created_at.desc(), ScanRun.id.desc())
        )
        return list(self.session.scalars(stmt).all())

    def list_job_observations(self, job_id: int) -> list[JobScanObservation]:
        stmt = (
            select(JobScanObservation)
            .where(JobScanObservation.job_posting_id == job_id)
            .order_by(JobScanObservation.observed_at.desc(), JobScanObservation.id.desc())
        )
        return list(self.session.scalars(stmt).all())

    def list_job_history(self, job_id: int) -> list[JobStatusHistory]:
        stmt = (
            select(JobStatusHistory)
            .where(JobStatusHistory.job_posting_id == job_id)
            .order_by(JobStatusHistory.created_at.desc(), JobStatusHistory.id.desc())
        )
        return list(self.session.scalars(stmt).all())

    def list_opportunities(self, filters: OpportunityFilters | None = None) -> list[JobPosting]:
        stmt: Select[tuple[JobPosting]] = (
            select(JobPosting)
            .options(joinedload(JobPosting.company))
            .order_by(
                JobPosting.first_seen_at.desc(),
                JobPosting.title.asc(),
            )
        )
        if filters:
            if filters.active_view == "queue":
                stmt = stmt.where(
                    JobPosting.review_status.in_(
                        [ReviewStatus.NOT_REVIEWED, ReviewStatus.INTERESTED]
                    )
                )
            if filters.company_id:
                stmt = stmt.where(JobPosting.company_id == int(filters.company_id))
            if filters.review_status:
                stmt = stmt.where(JobPosting.review_status == ReviewStatus(filters.review_status))
            if filters.career_site_status:
                stmt = stmt.where(
                    JobPosting.career_site_status == CareerSiteStatus(filters.career_site_status)
                )
            if filters.location:
                stmt = stmt.where(JobPosting.location.ilike(f"%{filters.location}%"))
            if filters.department:
                stmt = stmt.where(JobPosting.department.ilike(f"%{filters.department}%"))
            if filters.source_provider:
                stmt = stmt.where(JobPosting.source_provider == filters.source_provider)
            if filters.first_seen_from:
                stmt = stmt.where(JobPosting.first_seen_at >= filters.first_seen_from)
            if filters.first_seen_to:
                stmt = stmt.where(JobPosting.first_seen_at <= filters.first_seen_to)
            if filters.last_verified_from:
                stmt = stmt.where(JobPosting.last_verified_at >= filters.last_verified_from)
            if filters.last_verified_to:
                stmt = stmt.where(JobPosting.last_verified_at <= filters.last_verified_to)
            if filters.active_view == "removed":
                stmt = stmt.where(JobPosting.career_site_status == CareerSiteStatus.REMOVED)
        return list(self.session.scalars(stmt).all())

    def list_jobs_for_export(
        self,
        filters: OpportunityFilters | None = None,
        selected_ids: set[int] | None = None,
    ) -> list[JobPosting]:
        jobs = self.list_opportunities(filters)
        if selected_ids:
            return [job for job in jobs if job.id in selected_ids]
        return jobs

    def find_existing_job(
        self,
        *,
        company_id: int,
        source_provider: str,
        external_job_id: str | None,
        canonical_url: str | None,
        normalized_title: str,
        normalized_location: str | None,
        department: str | None,
    ) -> JobPosting | None:
        if external_job_id:
            stmt = select(JobPosting).where(
                JobPosting.company_id == company_id,
                JobPosting.source_provider == source_provider,
                JobPosting.external_job_id == external_job_id,
            )
            job = self.session.scalars(stmt).first()
            if job:
                return job

        if canonical_url:
            stmt = select(JobPosting).where(
                JobPosting.company_id == company_id,
                JobPosting.canonical_url == canonical_url,
            )
            job = self.session.scalars(stmt).first()
            if job:
                return job

        stmt = select(JobPosting).where(
            JobPosting.company_id == company_id,
            JobPosting.normalized_title == normalized_title,
            JobPosting.normalized_location == normalized_location,
            JobPosting.department == department,
            JobPosting.external_job_id.is_(None),
        )
        return self.session.scalars(stmt).first()

    def list_active_jobs_for_company(
        self, company_id: int, source_provider: str
    ) -> list[JobPosting]:
        stmt = select(JobPosting).where(
            JobPosting.company_id == company_id,
            JobPosting.source_provider == source_provider,
            JobPosting.career_site_status == CareerSiteStatus.ACTIVE,
        )
        return list(self.session.scalars(stmt).all())
