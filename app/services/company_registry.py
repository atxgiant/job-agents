from __future__ import annotations

import csv
import io
from dataclasses import asdict, dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditEvent, Company, CompanyAlias
from app.models.enums import ActorType, CompanyStatus, CompanyType
from app.repositories.audit_repository import AuditRepository
from app.repositories.company_repository import CompanyFilters, CompanyRepository
from app.services.scan_blocks import ScanBlockAssignmentService, ScanBlockPreview
from app.utils.company_text import normalize_company_name, split_csv_tags


class CompanyLifecycleError(ValueError):
    """Raised when a company lifecycle transition is invalid."""


@dataclass(slots=True)
class CSVImportRowResult:
    row_number: int
    outcome: str
    company_name: str
    details: str


@dataclass(slots=True)
class CSVImportReport:
    created: int
    updated: int
    skipped: int
    failed: int
    rows: list[CSVImportRowResult]


def company_to_audit_dict(company: Company) -> dict[str, Any]:
    return {
        "id": company.id,
        "name": company.name,
        "normalized_name": company.normalized_name,
        "website_url": company.website_url,
        "careers_url": company.careers_url,
        "ats_provider": company.ats_provider,
        "ats_company_identifier": company.ats_company_identifier,
        "company_type": company.company_type.value,
        "public_status": company.public_status,
        "ticker": company.ticker,
        "industry_tags": company.industry_tags,
        "product_tags": company.product_tags,
        "company_description": company.company_description,
        "headquarters_location": company.headquarters_location,
        "status": company.status.value,
        "scan_block": company.scan_block,
        "scan_frequency_override": company.scan_frequency_override,
        "seed_source": company.seed_source,
        "seed_run_id": company.seed_run_id,
        "seed_rationale": company.seed_rationale,
        "source_urls": company.source_urls,
        "rejection_reason": company.rejection_reason,
        "exclusion_reason": company.exclusion_reason,
        "last_scanned_at": company.last_scanned_at.isoformat() if company.last_scanned_at else None,
        "next_scheduled_scan_at": (
            company.next_scheduled_scan_at.isoformat() if company.next_scheduled_scan_at else None
        ),
        "scan_assignment_mode": company.scan_assignment_mode,
    }


class CompanyRegistryService:
    CSV_HEADERS = [
        "name",
        "website_url",
        "careers_url",
        "ats_provider",
        "ats_company_identifier",
        "company_type",
        "public_status",
        "ticker",
        "industry_tags",
        "product_tags",
        "company_description",
        "headquarters_location",
        "status",
        "scan_block",
        "scan_frequency_override",
        "seed_source",
        "seed_run_id",
        "seed_rationale",
        "source_urls",
        "rejection_reason",
        "exclusion_reason",
        "aliases",
    ]

    def __init__(self, session: Session) -> None:
        self.session = session
        self.company_repo = CompanyRepository(session)
        self.audit_repo = AuditRepository(session)
        self.scan_blocks = ScanBlockAssignmentService()

    def _log_event(
        self,
        *,
        event_type: str,
        actor_type: ActorType,
        company: Company | None,
        before_payload: dict[str, Any] | None,
        after_payload: dict[str, Any] | None,
        reason: str | None = None,
    ) -> AuditEvent:
        return self.audit_repo.add(
            AuditEvent(
                event_type=event_type,
                actor_type=actor_type,
                entity_type="company_registry",
                entity_id=str(company.id) if company else None,
                company_id=company.id if company else None,
                before_payload=before_payload,
                after_payload=after_payload,
                reason=reason,
            )
        )

    def list_companies(self, filters: CompanyFilters | None = None) -> list[Company]:
        return self.company_repo.list_companies(filters)

    def get_company(self, company_id: int) -> Company:
        company = self.company_repo.get(company_id)
        if not company:
            raise CompanyLifecycleError("Company not found.")
        return company

    def company_audit_timeline(self, company_id: int) -> list[AuditEvent]:
        return self.company_repo.list_audit_events(company_id)

    def create_company(
        self,
        *,
        actor_type: ActorType = ActorType.LOCAL_USER,
        payload: dict[str, Any] | None = None,
        **overrides: Any,
    ) -> Company:
        payload = {**(payload or {}), **overrides}
        name = payload["name"].strip()
        existing = self.company_repo.find_existing(
            name=name,
            website_url=payload.get("website_url"),
            ticker=payload.get("ticker"),
            aliases=split_csv_tags(payload.get("aliases")),
        )
        if existing:
            raise CompanyLifecycleError("A matching company already exists.")

        company = Company(
            name=name,
            normalized_name=normalize_company_name(name),
            website_url=payload.get("website_url") or None,
            careers_url=payload.get("careers_url") or None,
            ats_provider=payload.get("ats_provider") or None,
            ats_company_identifier=payload.get("ats_company_identifier") or None,
            company_type=CompanyType(payload.get("company_type", CompanyType.UNKNOWN.value)),
            public_status=payload.get("public_status") or None,
            ticker=(payload.get("ticker") or "").upper() or None,
            industry_tags=payload.get("industry_tags") or None,
            product_tags=payload.get("product_tags") or None,
            company_description=payload.get("company_description") or None,
            headquarters_location=payload.get("headquarters_location") or None,
            status=CompanyStatus(payload.get("status", CompanyStatus.ACTIVE.value)),
            scan_block=int(payload["scan_block"])
            if payload.get("scan_block") not in ("", None)
            else None,
            scan_frequency_override=payload.get("scan_frequency_override") or None,
            seed_source=payload.get("seed_source") or None,
            seed_run_id=payload.get("seed_run_id") or None,
            seed_rationale=payload.get("seed_rationale") or None,
            source_urls=payload.get("source_urls") or None,
            rejection_reason=payload.get("rejection_reason") or None,
            exclusion_reason=payload.get("exclusion_reason") or None,
            scan_assignment_mode="manual"
            if payload.get("scan_block") not in ("", None)
            else "auto",
        )
        self._normalize_status_dependent_fields(company)
        self._validate_reason_fields(
            company.status, company.rejection_reason, company.exclusion_reason
        )
        self.company_repo.add(company)
        self._replace_aliases(company, split_csv_tags(payload.get("aliases")))
        self._log_event(
            event_type="company_created",
            actor_type=actor_type,
            company=company,
            before_payload=None,
            after_payload=company_to_audit_dict(company),
        )
        self.session.commit()
        return company

    def update_company(
        self,
        company_id: int,
        *,
        actor_type: ActorType = ActorType.LOCAL_USER,
        payload: dict[str, Any] | None = None,
        **overrides: Any,
    ) -> Company:
        payload = {**(payload or {}), **overrides}
        company = self.get_company(company_id)
        before_payload = company_to_audit_dict(company)
        company.name = payload["name"].strip()
        company.normalized_name = normalize_company_name(company.name)
        company.website_url = payload.get("website_url") or None
        company.careers_url = payload.get("careers_url") or None
        company.ats_provider = payload.get("ats_provider") or None
        company.ats_company_identifier = payload.get("ats_company_identifier") or None
        company.company_type = CompanyType(payload.get("company_type", company.company_type.value))
        company.public_status = payload.get("public_status") or None
        company.ticker = (payload.get("ticker") or "").upper() or None
        company.industry_tags = payload.get("industry_tags") or None
        company.product_tags = payload.get("product_tags") or None
        company.company_description = payload.get("company_description") or None
        company.headquarters_location = payload.get("headquarters_location") or None
        company.scan_frequency_override = payload.get("scan_frequency_override") or None
        company.seed_source = payload.get("seed_source") or None
        company.seed_run_id = payload.get("seed_run_id") or None
        company.seed_rationale = payload.get("seed_rationale") or None
        company.source_urls = payload.get("source_urls") or None
        self._replace_aliases(company, split_csv_tags(payload.get("aliases")))
        self._normalize_status_dependent_fields(company)
        self._log_event(
            event_type="company_edited",
            actor_type=actor_type,
            company=company,
            before_payload=before_payload,
            after_payload=company_to_audit_dict(company),
        )
        self.session.commit()
        return company

    def activate_company(
        self, company_id: int, actor_type: ActorType = ActorType.LOCAL_USER
    ) -> Company:
        company = self.get_company(company_id)
        if company.status in {CompanyStatus.REJECTED, CompanyStatus.EXCLUDED}:
            raise CompanyLifecycleError(
                "Rejected or excluded companies require explicit reactivation."
            )
        return self._transition_status(
            company, CompanyStatus.ACTIVE, "company_activated", actor_type
        )

    def deactivate_company(
        self, company_id: int, actor_type: ActorType = ActorType.LOCAL_USER
    ) -> Company:
        company = self.get_company(company_id)
        if company.status != CompanyStatus.ACTIVE:
            raise CompanyLifecycleError("Only active companies can be deactivated.")
        return self._transition_status(
            company, CompanyStatus.INACTIVE, "company_deactivated", actor_type
        )

    def reject_company(
        self,
        company_id: int,
        reason: str,
        actor_type: ActorType = ActorType.LOCAL_USER,
    ) -> Company:
        company = self.get_company(company_id)
        if company.status == CompanyStatus.REJECTED:
            raise CompanyLifecycleError("Company is already rejected.")
        if not reason.strip():
            raise CompanyLifecycleError("Rejecting a company requires a rejection reason.")
        company.rejection_reason = reason.strip()
        company.exclusion_reason = None
        return self._transition_status(
            company,
            CompanyStatus.REJECTED,
            "company_rejected",
            actor_type,
            reason=company.rejection_reason,
        )

    def exclude_company(
        self,
        company_id: int,
        reason: str,
        actor_type: ActorType = ActorType.LOCAL_USER,
    ) -> Company:
        company = self.get_company(company_id)
        if company.status == CompanyStatus.EXCLUDED:
            raise CompanyLifecycleError("Company is already excluded.")
        if not reason.strip():
            raise CompanyLifecycleError("Excluding a company requires an exclusion reason.")
        company.exclusion_reason = reason.strip()
        company.rejection_reason = None
        return self._transition_status(
            company,
            CompanyStatus.EXCLUDED,
            "company_excluded",
            actor_type,
            reason=company.exclusion_reason,
        )

    def reactivate_company(
        self, company_id: int, actor_type: ActorType = ActorType.LOCAL_USER
    ) -> Company:
        company = self.get_company(company_id)
        if company.status not in {CompanyStatus.REJECTED, CompanyStatus.EXCLUDED}:
            raise CompanyLifecycleError("Only rejected or excluded companies can be reactivated.")
        company.rejection_reason = None
        company.exclusion_reason = None
        return self._transition_status(
            company, CompanyStatus.ACTIVE, "company_reactivated", actor_type
        )

    def assign_scan_block(
        self,
        company_id: int,
        scan_block: int | None,
        actor_type: ActorType = ActorType.LOCAL_USER,
    ) -> Company:
        company = self.get_company(company_id)
        before_payload = company_to_audit_dict(company)
        company.scan_block = scan_block
        company.scan_assignment_mode = "manual" if scan_block is not None else "auto"
        self._log_event(
            event_type="scan_block_changed",
            actor_type=actor_type,
            company=company,
            before_payload=before_payload,
            after_payload=company_to_audit_dict(company),
            reason=f"Assigned scan block {scan_block}"
            if scan_block is not None
            else "Cleared scan block",
        )
        self.session.commit()
        return company

    def preview_rebalance(self, *, total_blocks: int) -> list[ScanBlockPreview]:
        companies = self.company_repo.list_active_for_scan_assignment()
        return self.scan_blocks.preview_rebalance(companies, total_blocks=total_blocks)

    def rebalance_scan_blocks(
        self,
        *,
        total_blocks: int,
        actor_type: ActorType = ActorType.LOCAL_USER,
    ) -> list[ScanBlockPreview]:
        companies = self.company_repo.list_active_for_scan_assignment()
        before_payload = {company.id: company_to_audit_dict(company) for company in companies}
        previews = self.scan_blocks.apply_rebalance(companies, total_blocks=total_blocks)
        for company in companies:
            if company.scan_assignment_mode == "auto":
                self._log_event(
                    event_type="scan_block_changed",
                    actor_type=actor_type,
                    company=company,
                    before_payload=before_payload[company.id],
                    after_payload=company_to_audit_dict(company),
                    reason="Automatic scan-block rebalance",
                )
        self.session.commit()
        return previews

    def export_companies_csv(
        self,
        filters: CompanyFilters | None = None,
        selected_ids: set[int] | None = None,
        actor_type: ActorType = ActorType.LOCAL_USER,
    ) -> str:
        companies = self.list_companies(filters)
        if selected_ids:
            companies = [company for company in companies if company.id in selected_ids]
        output = io.StringIO()
        writer = csv.DictWriter(
            output, fieldnames=["id", *self.CSV_HEADERS, "created_at", "updated_at"]
        )
        writer.writeheader()
        for company in companies:
            writer.writerow(
                {
                    "id": company.id,
                    "name": company.name,
                    "website_url": company.website_url,
                    "careers_url": company.careers_url,
                    "ats_provider": company.ats_provider,
                    "ats_company_identifier": company.ats_company_identifier,
                    "company_type": company.company_type.value,
                    "public_status": company.public_status,
                    "ticker": company.ticker,
                    "industry_tags": company.industry_tags,
                    "product_tags": company.product_tags,
                    "company_description": company.company_description,
                    "headquarters_location": company.headquarters_location,
                    "status": company.status.value,
                    "scan_block": company.scan_block,
                    "scan_frequency_override": company.scan_frequency_override,
                    "seed_source": company.seed_source,
                    "seed_run_id": company.seed_run_id,
                    "seed_rationale": company.seed_rationale,
                    "source_urls": company.source_urls,
                    "rejection_reason": company.rejection_reason,
                    "exclusion_reason": company.exclusion_reason,
                    "aliases": ", ".join(alias.alias for alias in company.aliases),
                    "created_at": company.created_at.isoformat(),
                    "updated_at": company.updated_at.isoformat(),
                }
            )
        self._log_event(
            event_type="companies_csv_exported",
            actor_type=actor_type,
            company=None,
            before_payload=None,
            after_payload={"count": len(companies)},
            reason="CSV export",
        )
        self.session.commit()
        return output.getvalue()

    def import_companies_csv(
        self,
        csv_text: str,
        actor_type: ActorType = ActorType.LOCAL_USER,
    ) -> CSVImportReport:
        reader = csv.DictReader(io.StringIO(csv_text))
        missing_headers = [
            header for header in self.CSV_HEADERS if header not in (reader.fieldnames or [])
        ]
        if missing_headers:
            raise CompanyLifecycleError(
                f"CSV is missing required headers: {', '.join(missing_headers)}"
            )

        created = updated = skipped = failed = 0
        results: list[CSVImportRowResult] = []
        for row_number, row in enumerate(reader, start=2):
            try:
                outcome, details = self._import_row(row)
                if outcome == "created":
                    created += 1
                elif outcome == "updated":
                    updated += 1
                else:
                    skipped += 1
                results.append(
                    CSVImportRowResult(
                        row_number=row_number,
                        outcome=outcome,
                        company_name=row.get("name", ""),
                        details=details,
                    )
                )
            except Exception as exc:
                failed += 1
                results.append(
                    CSVImportRowResult(
                        row_number=row_number,
                        outcome="failed",
                        company_name=row.get("name", ""),
                        details=str(exc),
                    )
                )
        self._log_event(
            event_type="companies_csv_imported",
            actor_type=actor_type,
            company=None,
            before_payload=None,
            after_payload=asdict(CSVImportReport(created, updated, skipped, failed, results)),
            reason="CSV import",
        )
        self.session.commit()
        return CSVImportReport(created, updated, skipped, failed, results)

    def upsert_seed_candidate(
        self,
        *,
        name: str,
        website_url: str | None,
        ticker: str | None,
        seed_source: str,
        seed_run_id: str | None = None,
        seed_rationale: str | None = None,
    ) -> tuple[Company, str]:
        existing = self.company_repo.find_existing(
            name=name, website_url=website_url, ticker=ticker
        )
        if existing:
            if existing.status == CompanyStatus.REJECTED:
                return existing, "blocked_rejected"
            if existing.status == CompanyStatus.EXCLUDED:
                return existing, "blocked_excluded"
            existing.seed_source = seed_source
            existing.seed_run_id = seed_run_id
            existing.seed_rationale = seed_rationale
            self.session.commit()
            return existing, "merged"
        company = self.create_company(
            name=name,
            website_url=website_url,
            ticker=ticker,
            seed_source=seed_source,
            seed_run_id=seed_run_id,
            seed_rationale=seed_rationale,
            status=CompanyStatus.ACTIVE.value,
            actor_type=ActorType.SYSTEM,
        )
        return company, "inserted"

    def _import_row(self, row: dict[str, str]) -> tuple[str, str]:
        name = row["name"].strip()
        status = CompanyStatus(row["status"] or CompanyStatus.ACTIVE.value)
        aliases = split_csv_tags(row.get("aliases"))
        existing = self.company_repo.find_existing(
            name=name,
            website_url=row.get("website_url"),
            ticker=row.get("ticker"),
            aliases=aliases,
        )
        if existing:
            before_payload = company_to_audit_dict(existing)
            existing.name = name
            existing.normalized_name = normalize_company_name(name)
            existing.website_url = row.get("website_url") or None
            existing.careers_url = row.get("careers_url") or None
            existing.ats_provider = row.get("ats_provider") or None
            existing.ats_company_identifier = row.get("ats_company_identifier") or None
            existing.company_type = CompanyType(
                row.get("company_type") or CompanyType.UNKNOWN.value
            )
            existing.public_status = row.get("public_status") or None
            existing.ticker = (row.get("ticker") or "").upper() or None
            existing.industry_tags = row.get("industry_tags") or None
            existing.product_tags = row.get("product_tags") or None
            existing.company_description = row.get("company_description") or None
            existing.headquarters_location = row.get("headquarters_location") or None
            existing.scan_frequency_override = row.get("scan_frequency_override") or None
            existing.seed_source = row.get("seed_source") or None
            existing.seed_run_id = row.get("seed_run_id") or None
            existing.seed_rationale = row.get("seed_rationale") or None
            existing.source_urls = row.get("source_urls") or None
            self._replace_aliases(existing, aliases)
            if existing.status not in {CompanyStatus.REJECTED, CompanyStatus.EXCLUDED}:
                existing.status = status
                existing.rejection_reason = row.get("rejection_reason") or None
                existing.exclusion_reason = row.get("exclusion_reason") or None
                if row.get("scan_block") not in ("", None):
                    existing.scan_block = int(row["scan_block"])
                    existing.scan_assignment_mode = "manual"
            self._normalize_status_dependent_fields(existing)
            self._log_event(
                event_type="company_edited",
                actor_type=ActorType.SYSTEM,
                company=existing,
                before_payload=before_payload,
                after_payload=company_to_audit_dict(existing),
                reason="CSV import upsert",
            )
            return "updated", "Existing company updated."
        self.create_company(actor_type=ActorType.SYSTEM, payload=row)
        return "created", "New company created."

    def _replace_aliases(self, company: Company, aliases: list[str]) -> None:
        company.aliases.clear()
        for alias in aliases:
            company.aliases.append(
                CompanyAlias(alias=alias, normalized_alias=normalize_company_name(alias))
            )

    def _transition_status(
        self,
        company: Company,
        target_status: CompanyStatus,
        event_type: str,
        actor_type: ActorType,
        reason: str | None = None,
    ) -> Company:
        before_payload = company_to_audit_dict(company)
        company.status = target_status
        self._normalize_status_dependent_fields(company)
        self._validate_reason_fields(
            company.status, company.rejection_reason, company.exclusion_reason
        )
        self._log_event(
            event_type=event_type,
            actor_type=actor_type,
            company=company,
            before_payload=before_payload,
            after_payload=company_to_audit_dict(company),
            reason=reason,
        )
        self.session.commit()
        return company

    def _validate_reason_fields(
        self,
        status: CompanyStatus,
        rejection_reason: str | None,
        exclusion_reason: str | None,
    ) -> None:
        if status == CompanyStatus.REJECTED and not (rejection_reason or "").strip():
            raise CompanyLifecycleError("Rejected companies require a rejection reason.")
        if status == CompanyStatus.EXCLUDED and not (exclusion_reason or "").strip():
            raise CompanyLifecycleError("Excluded companies require an exclusion reason.")

    def _normalize_status_dependent_fields(self, company: Company) -> None:
        if company.status != CompanyStatus.REJECTED:
            company.rejection_reason = None
        if company.status != CompanyStatus.EXCLUDED:
            company.exclusion_reason = None
