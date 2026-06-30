from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, enum_type
from app.models.enums import CareerSiteStatus, ReviewStatus

if TYPE_CHECKING:
    from app.models.company import Company


class JobPosting(TimestampMixin, Base):
    __tablename__ = "job_postings"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True, nullable=False)
    external_job_id: Mapped[str | None] = mapped_column(String(255), index=True)
    source_provider: Mapped[str | None] = mapped_column(String(100))
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
    job_description_text: Mapped[str | None] = mapped_column(Text)
    job_description_hash: Mapped[str | None] = mapped_column(String(128), index=True)
    job_summary: Mapped[str | None] = mapped_column(Text)
    fit_score: Mapped[float | None] = mapped_column(Float)
    competitiveness_score: Mapped[float | None] = mapped_column(Float)
    interest_score: Mapped[float | None] = mapped_column(Float)
    priority_score: Mapped[float | None] = mapped_column(Float, index=True)
    fit_explanation: Mapped[str | None] = mapped_column(Text)
    skill_matches: Mapped[str | None] = mapped_column(Text)
    skill_gaps: Mapped[str | None] = mapped_column(Text)
    role_family: Mapped[str | None] = mapped_column(String(255), index=True)
    review_status: Mapped[ReviewStatus] = mapped_column(
        enum_type(ReviewStatus), default=ReviewStatus.NOT_REVIEWED, index=True, nullable=False
    )
    career_site_status: Mapped[CareerSiteStatus] = mapped_column(
        enum_type(CareerSiteStatus),
        default=CareerSiteStatus.ACTIVE,
        index=True,
        nullable=False,
    )
    user_notes: Mapped[str | None] = mapped_column(Text)

    company: Mapped[Company] = relationship(back_populates="job_postings")
