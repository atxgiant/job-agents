from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import CompanyLifecycle, CompanyType

if TYPE_CHECKING:
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
        Enum(CompanyType), default=CompanyType.UNKNOWN, nullable=False
    )
    lifecycle_state: Mapped[CompanyLifecycle] = mapped_column(
        Enum(CompanyLifecycle), default=CompanyLifecycle.ACTIVE, index=True, nullable=False
    )
    public_status: Mapped[str | None] = mapped_column(String(100))
    ticker: Mapped[str | None] = mapped_column(String(20), index=True)
    industry_tags: Mapped[str | None] = mapped_column(Text)
    product_tags: Mapped[str | None] = mapped_column(Text)
    company_description: Mapped[str | None] = mapped_column(Text)
    headquarters_location: Mapped[str | None] = mapped_column(String(255))
    active_for_scanning: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    rejected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    excluded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    exclusion_reason: Mapped[str | None] = mapped_column(Text)
    scan_block: Mapped[int | None] = mapped_column(Integer, index=True)
    scan_frequency_override: Mapped[str | None] = mapped_column(String(100))
    last_scan_status: Mapped[str | None] = mapped_column(String(100))
    last_scan_error: Mapped[str | None] = mapped_column(Text)
    seed_source: Mapped[str | None] = mapped_column(String(255))
    seed_prompt_version: Mapped[str | None] = mapped_column(String(255))
    seed_run_id: Mapped[str | None] = mapped_column(String(255), index=True)
    seed_rationale: Mapped[str | None] = mapped_column(Text)
    source_urls: Mapped[str | None] = mapped_column(Text)

    aliases: Mapped[list[CompanyAlias]] = relationship(back_populates="company")
    job_postings: Mapped[list[JobPosting]] = relationship(back_populates="company")


class CompanyAlias(TimestampMixin, Base):
    __tablename__ = "company_aliases"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    alias: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    normalized_alias: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    company: Mapped[Company] = relationship(back_populates="aliases")
