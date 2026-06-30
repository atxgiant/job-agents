from __future__ import annotations

from app.models import Company
from app.models.enums import CompanyStatus, CompanyType
from app.repositories.audit_repository import AuditRepository
from app.repositories.company_repository import CompanyRepository
from app.repositories.job_repository import JobRepository
from app.services.company_scan import CompanyScanError, CompanyScanService


def make_company(db_session, **overrides):
    payload = {
        "name": "Acme Robotics",
        "normalized_name": "acme robotics",
        "company_type": CompanyType.PUBLIC,
        "status": CompanyStatus.ACTIVE,
        "ats_provider": "greenhouse",
        "ats_company_identifier": "acme",
    }
    payload.update(overrides)
    company = Company(**payload)
    db_session.add(company)
    db_session.commit()
    return company


def build_service(db_session):
    return CompanyScanService(
        CompanyRepository(db_session),
        JobRepository(db_session),
        AuditRepository(db_session),
    )


def test_company_scan_denied_for_inactive_company(db_session):
    company = make_company(db_session, status=CompanyStatus.INACTIVE)
    service = build_service(db_session)

    try:
        service.scan_company_greenhouse(company.id)
    except CompanyScanError as exc:
        assert exc.error_code == "company_not_scan_eligible"
    else:
        raise AssertionError("Expected CompanyScanError")


def test_company_scan_denied_for_missing_greenhouse_configuration(db_session):
    company = make_company(
        db_session, ats_company_identifier=None, careers_url="https://example.com"
    )
    service = build_service(db_session)

    try:
        service.scan_company_greenhouse(company.id)
    except CompanyScanError as exc:
        assert exc.error_code == "missing_ats_configuration"
    else:
        raise AssertionError("Expected CompanyScanError")
