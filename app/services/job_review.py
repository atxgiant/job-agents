from __future__ import annotations

from datetime import UTC, datetime

from app.models import JobStatusHistory
from app.models.enums import ActorType, ReviewStatus
from app.repositories.job_repository import JobRepository


class JobReviewError(ValueError):
    pass


class JobReviewService:
    def __init__(self, repository: JobRepository) -> None:
        self.repository = repository

    def update_review_status(
        self,
        job_id: int,
        *,
        new_status: ReviewStatus,
        reason: str | None = None,
        applied_at: datetime | None = None,
    ) -> None:
        job = self.repository.get_job(job_id)
        if not job:
            raise JobReviewError("Job not found.")
        previous_status = job.review_status
        now = datetime.now(UTC)
        job.review_status = new_status
        job.reviewed_at = now
        if new_status == ReviewStatus.APPLIED:
            job.applied_at = applied_at or now
        if new_status == ReviewStatus.REJECTED:
            job.rejected_at = now
            job.rejection_reason = reason or None
        if new_status != ReviewStatus.REJECTED:
            job.rejected_at = None
            job.rejection_reason = None
        if new_status != ReviewStatus.APPLIED:
            job.applied_at = None if previous_status != ReviewStatus.APPLIED else job.applied_at
        self.repository.add_status_history(
            JobStatusHistory(
                job_posting_id=job.id,
                event_type="review_status_changed",
                actor_type=ActorType.LOCAL_USER,
                previous_review_status=previous_status,
                new_review_status=new_status,
                previous_career_site_status=None,
                new_career_site_status=None,
                reason=reason,
                metadata_json={},
            )
        )

    def update_notes(self, job_id: int, notes: str | None) -> None:
        job = self.repository.get_job(job_id)
        if not job:
            raise JobReviewError("Job not found.")
        previous_notes = job.user_notes
        job.user_notes = notes or None
        self.repository.add_status_history(
            JobStatusHistory(
                job_posting_id=job.id,
                event_type="user_notes_updated",
                actor_type=ActorType.LOCAL_USER,
                previous_review_status=None,
                new_review_status=None,
                previous_career_site_status=None,
                new_career_site_status=None,
                reason="User updated notes.",
                metadata_json={
                    "previous_notes": previous_notes,
                    "new_notes": job.user_notes,
                },
            )
        )
