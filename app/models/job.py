from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, enum_type
from app.models.enums import ActorType, CareerSiteStatus, ReviewStatus

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.run import ScanRun


class JobPosting(TimestampMixin, Base):
    __tablename__ = "job_postings"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True, nullable=False)
    external_job_id: Mapped[str | None] = mapped_column(String(255), index=True)
    source_provider: Mapped[str | None] = mapped_column(String(100), index=True)
    source_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    canonical_url: Mapped[str | None] = mapped_column(String(1000), index=True)
    application_url: Mapped[str | None] = mapped_column(String(1000))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_title: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    location: Mapped[str | None] = mapped_column(String(255))
    normalized_location: Mapped[str | None] = mapped_column(String(255), index=True)
    department: Mapped[str | None] = mapped_column(String(255))
    employment_type: Mapped[str | None] = mapped_column(String(100))
    work_arrangement: Mapped[str | None] = mapped_column(String(100))
    salary_text: Mapped[str | None] = mapped_column(String(255))
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    career_site_status: Mapped[CareerSiteStatus] = mapped_column(
        enum_type(CareerSiteStatus),
        default=CareerSiteStatus.ACTIVE,
        index=True,
        nullable=False,
    )
    career_site_status_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    job_description_text: Mapped[str | None] = mapped_column(Text)
    job_description_hash: Mapped[str | None] = mapped_column(String(128), index=True)
    job_summary: Mapped[str | None] = mapped_column(Text)
    review_status: Mapped[ReviewStatus] = mapped_column(
        enum_type(ReviewStatus),
        default=ReviewStatus.NOT_REVIEWED,
        index=True,
        nullable=False,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    user_notes: Mapped[str | None] = mapped_column(Text)
    provider_metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    company: Mapped[Company] = relationship(back_populates="job_postings")
    scan_observations: Mapped[list[JobScanObservation]] = relationship(
        back_populates="job_posting",
        cascade="all, delete-orphan",
    )
    status_history: Mapped[list[JobStatusHistory]] = relationship(
        back_populates="job_posting",
        cascade="all, delete-orphan",
    )


class JobScanObservation(TimestampMixin, Base):
    __tablename__ = "job_scan_observations"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_posting_id: Mapped[int] = mapped_column(
        ForeignKey("job_postings.id"),
        index=True,
        nullable=False,
    )
    scan_run_id: Mapped[int] = mapped_column(ForeignKey("scan_runs.id"), index=True, nullable=False)
    observed_status: Mapped[CareerSiteStatus] = mapped_column(
        enum_type(CareerSiteStatus),
        nullable=False,
    )
    source_payload_hash: Mapped[str | None] = mapped_column(String(128))
    title_snapshot: Mapped[str | None] = mapped_column(String(255))
    location_snapshot: Mapped[str | None] = mapped_column(String(255))
    department_snapshot: Mapped[str | None] = mapped_column(String(255))
    description_hash_snapshot: Mapped[str | None] = mapped_column(String(128))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    job_posting: Mapped[JobPosting] = relationship(back_populates="scan_observations")
    scan_run: Mapped[ScanRun] = relationship(back_populates="job_observations")


class JobStatusHistory(TimestampMixin, Base):
    __tablename__ = "job_status_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_posting_id: Mapped[int] = mapped_column(
        ForeignKey("job_postings.id"),
        index=True,
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(100), index=True)
    actor_type: Mapped[ActorType] = mapped_column(enum_type(ActorType), nullable=False, index=True)
    previous_review_status: Mapped[ReviewStatus | None] = mapped_column(enum_type(ReviewStatus))
    new_review_status: Mapped[ReviewStatus | None] = mapped_column(enum_type(ReviewStatus))
    previous_career_site_status: Mapped[CareerSiteStatus | None] = mapped_column(
        enum_type(CareerSiteStatus)
    )
    new_career_site_status: Mapped[CareerSiteStatus | None] = mapped_column(
        enum_type(CareerSiteStatus)
    )
    reason: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    job_posting: Mapped[JobPosting] = relationship(back_populates="status_history")
