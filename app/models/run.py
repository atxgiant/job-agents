from __future__ import annotations

from sqlalchemy import Enum, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin
from app.models.enums import WorkflowStatus


class ScanRun(TimestampMixin, Base):
    __tablename__ = "scan_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_type: Mapped[str] = mapped_column(String(100), index=True)
    workflow_run_id: Mapped[str | None] = mapped_column(String(255), index=True)
    scope: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[WorkflowStatus] = mapped_column(
        Enum(WorkflowStatus), default=WorkflowStatus.PENDING, nullable=False, index=True
    )
    jobs_discovered: Mapped[int] = mapped_column(default=0, nullable=False)
    jobs_updated: Mapped[int] = mapped_column(default=0, nullable=False)
    jobs_marked_removed: Mapped[int] = mapped_column(default=0, nullable=False)
    errors: Mapped[str | None] = mapped_column(Text)


class WorkflowRun(TimestampMixin, Base):
    __tablename__ = "workflow_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_name: Mapped[str] = mapped_column(String(100), index=True)
    workflow_run_id: Mapped[str | None] = mapped_column(String(255), index=True)
    status: Mapped[WorkflowStatus] = mapped_column(
        Enum(WorkflowStatus), default=WorkflowStatus.PENDING, nullable=False, index=True
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
