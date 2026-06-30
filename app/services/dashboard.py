from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select

from app.models import Company, JobPosting
from app.models.enums import CompanyLifecycle, ReviewStatus
from app.repositories.db import get_session


@dataclass(slots=True)
class DashboardStats:
    active_companies: int
    rejected_or_excluded_companies: int
    new_jobs: int
    interested_jobs: int
    applied_jobs: int


class DashboardService:
    def get_stats(self) -> DashboardStats:
        with get_session() as session:
            active_companies = session.scalar(
                select(func.count()).select_from(Company).where(
                    Company.lifecycle_state == CompanyLifecycle.ACTIVE
                )
            )
            rejected_or_excluded = session.scalar(
                select(func.count()).select_from(Company).where(
                    Company.lifecycle_state.in_(
                        [CompanyLifecycle.REJECTED, CompanyLifecycle.EXCLUDED]
                    )
                )
            )
            new_jobs = session.scalar(
                select(func.count()).select_from(JobPosting).where(
                    JobPosting.review_status == ReviewStatus.NOT_REVIEWED
                )
            )
            interested_jobs = session.scalar(
                select(func.count()).select_from(JobPosting).where(
                    JobPosting.review_status == ReviewStatus.INTERESTED
                )
            )
            applied_jobs = session.scalar(
                select(func.count()).select_from(JobPosting).where(
                    JobPosting.review_status == ReviewStatus.APPLIED
                )
            )
        return DashboardStats(
            active_companies=active_companies or 0,
            rejected_or_excluded_companies=rejected_or_excluded or 0,
            new_jobs=new_jobs or 0,
            interested_jobs=interested_jobs or 0,
            applied_jobs=applied_jobs or 0,
        )
