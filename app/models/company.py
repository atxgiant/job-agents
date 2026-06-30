from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, enum_type
from app.models.enums import CompanyStatus, CompanyType

if TYPE_CHECKING:
    from app.models.audit import AuditEvent
    from app.models.job import JobPosting


class Company(TimestampMixin, Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    website_url: Mapped[str | None] = mapped_column(String(500))
    careers_url: Mapped[str | None] = mapped_column(String(500))
    ats_provider: Mapped[str | None] = mapped_column(String(100))
    ats_company_identifier: Mapped[str | None] = mapped_column(String(255))
    company_type: Mapped[CompanyType] = mapped_column(
        enum_type(CompanyType), default=CompanyType.UNKNOWN, nullable=False, index=True
    )
    public_status: Mapped[str | None] = mapped_column(String(100))
    ticker: Mapped[str | None] = mapped_column(String(20), index=True)
    industry_tags: Mapped[str | None] = mapped_column(Text)
    product_tags: Mapped[str | None] = mapped_column(Text)
    company_description: Mapped[str | None] = mapped_column(Text)
    headquarters_location: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[CompanyStatus] = mapped_column(
        enum_type(CompanyStatus), default=CompanyStatus.ACTIVE, index=True, nullable=False
    )
    scan_block: Mapped[int | None] = mapped_column(Integer, index=True)
    scan_frequency_override: Mapped[str | None] = mapped_column(String(100))
    seed_source: Mapped[str | None] = mapped_column(String(255), index=True)
    seed_run_id: Mapped[str | None] = mapped_column(String(255), index=True)
    seed_rationale: Mapped[str | None] = mapped_column(Text)
    source_urls: Mapped[str | None] = mapped_column(Text)
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    exclusion_reason: Mapped[str | None] = mapped_column(Text)
    last_scanned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_scheduled_scan_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scan_assignment_mode: Mapped[str] = mapped_column(String(20), default="auto", nullable=False)

    aliases: Mapped[list[CompanyAlias]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )
    audit_events: Mapped[list[AuditEvent]] = relationship(back_populates="company")
    job_postings: Mapped[list[JobPosting]] = relationship(back_populates="company")

    @hybrid_property
    def active_for_scanning(self) -> bool:
        return self.status == CompanyStatus.ACTIVE


class CompanyAlias(TimestampMixin, Base):
    __tablename__ = "company_aliases"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    alias: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    normalized_alias: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    company: Mapped[Company] = relationship(back_populates="aliases")
