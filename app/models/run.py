from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, enum_type
from app.models.enums import ScanRunStatus, ScanType, WorkflowStatus

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.job import JobScanObservation


class ScanRun(TimestampMixin, Base):
    __tablename__ = "scan_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), index=True)
    scan_type: Mapped[ScanType] = mapped_column(enum_type(ScanType), nullable=False, index=True)
    source_provider: Mapped[str | None] = mapped_column(String(100), index=True)
    status: Mapped[ScanRunStatus] = mapped_column(
        enum_type(ScanRunStatus),
        default=ScanRunStatus.PENDING,
        nullable=False,
        index=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    jobs_discovered_count: Mapped[int] = mapped_column(default=0, nullable=False)
    jobs_created_count: Mapped[int] = mapped_column(default=0, nullable=False)
    jobs_updated_count: Mapped[int] = mapped_column(default=0, nullable=False)
    jobs_marked_removed_count: Mapped[int] = mapped_column(default=0, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)
    request_metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    company: Mapped[Company | None] = relationship(back_populates="scan_runs")
    job_observations: Mapped[list[JobScanObservation]] = relationship(back_populates="scan_run")


class WorkflowRun(TimestampMixin, Base):
    __tablename__ = "workflow_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_name: Mapped[str] = mapped_column(String(100), index=True)
    workflow_run_id: Mapped[str | None] = mapped_column(String(255), index=True)
    status: Mapped[WorkflowStatus] = mapped_column(
        enum_type(WorkflowStatus),
        default=WorkflowStatus.PENDING,
        nullable=False,
        index=True,
    )
    summary: Mapped[str | None] = mapped_column(Text)


class LLMUsageRecord(TimestampMixin, Base):
    __tablename__ = "llm_usage_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(100), index=True)
    model: Mapped[str] = mapped_column(String(255))
    operation: Mapped[str] = mapped_column(String(100), index=True)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    prompt_hash: Mapped[str | None] = mapped_column(String(128), index=True)
    response_hash: Mapped[str | None] = mapped_column(String(128))
