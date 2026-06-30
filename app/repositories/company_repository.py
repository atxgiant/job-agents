from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session

from app.models import AuditEvent, Company, CompanyAlias
from app.models.enums import CompanyStatus, CompanyType
from app.utils.company_text import normalize_company_name, normalize_domain


@dataclass(slots=True)
class CompanyFilters:
    search: str = ""
    status: str = ""
    scan_block: str = ""
    company_type: str = ""
    industry_tag: str = ""
    seed_source: str = ""
    ticker: str = ""


class CompanyRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, company: Company) -> Company:
        self.session.add(company)
        self.session.flush()
        return company

    def get(self, company_id: int) -> Company | None:
        return self.session.get(Company, company_id)

    def list_companies(self, filters: CompanyFilters | None = None) -> list[Company]:
        stmt: Select[tuple[Company]] = select(Company).order_by(Company.name.asc())
        if filters:
            if filters.search:
                needle = f"%{filters.search.lower()}%"
                stmt = stmt.where(
                    or_(
                        Company.name.ilike(needle),
                        Company.normalized_name.ilike(needle),
                        Company.website_url.ilike(needle),
                    )
                )
            if filters.status:
                stmt = stmt.where(Company.status == CompanyStatus(filters.status))
            if filters.scan_block:
                stmt = stmt.where(Company.scan_block == int(filters.scan_block))
            if filters.company_type:
                stmt = stmt.where(Company.company_type == CompanyType(filters.company_type))
            if filters.industry_tag:
                stmt = stmt.where(Company.industry_tags.ilike(f"%{filters.industry_tag}%"))
            if filters.seed_source:
                stmt = stmt.where(Company.seed_source == filters.seed_source)
            if filters.ticker:
                stmt = stmt.where(Company.ticker == filters.ticker.upper())
        return list(self.session.scalars(stmt).all())

    def list_active_for_scan_assignment(self) -> list[Company]:
        stmt = (
            select(Company)
            .where(Company.status == CompanyStatus.ACTIVE)
            .order_by(Company.scan_block.asc().nullsfirst(), Company.name.asc())
        )
        return list(self.session.scalars(stmt).all())

    def list_audit_events(self, company_id: int) -> list[AuditEvent]:
        stmt = (
            select(AuditEvent)
            .where(AuditEvent.company_id == company_id)
            .order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc())
        )
        return list(self.session.scalars(stmt).all())

    def find_existing(
        self,
        *,
        name: str,
        website_url: str | None = None,
        ticker: str | None = None,
        aliases: list[str] | None = None,
    ) -> Company | None:
        normalized_name = normalize_company_name(name)
        domain = normalize_domain(website_url)
        alias_values = [normalize_company_name(alias) for alias in aliases or []]
        conditions = [Company.normalized_name == normalized_name]
        if ticker:
            conditions.append(Company.ticker == ticker.upper())

        candidates = list(self.session.scalars(select(Company).where(or_(*conditions))).all())

        if domain:
            for company in self.list_companies():
                if normalize_domain(company.website_url) == domain:
                    return company

        if alias_values:
            alias_stmt = (
                select(CompanyAlias)
                .where(CompanyAlias.normalized_alias.in_(alias_values))
                .order_by(CompanyAlias.id.asc())
            )
            alias_match: CompanyAlias | None = self.session.scalars(alias_stmt).first()
            if alias_match:
                return alias_match.company

        return candidates[0] if candidates else None
