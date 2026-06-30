from __future__ import annotations

from datetime import UTC, datetime

from app.models import Company, JobPosting, ScanRun
from app.models.enums import (
    CareerSiteStatus,
    CompanyStatus,
    CompanyType,
    ReviewStatus,
    ScanRunStatus,
    ScanType,
)
from app.repositories.job_repository import JobRepository
from app.schemas.jobs import NormalizedJobPosting
from app.services.job_ingestion import JobIngestionService


def make_company(db_session):
    company = Company(
        name="Acme Robotics",
        normalized_name="acme robotics",
        company_type=CompanyType.PUBLIC,
        status=CompanyStatus.ACTIVE,
    )
    db_session.add(company)
    db_session.flush()
    return company


def make_scan_run(db_session, company_id: int):
    scan_run = ScanRun(
        company_id=company_id,
        scan_type=ScanType.MANUAL_GREENHOUSE,
        source_provider="greenhouse",
        status=ScanRunStatus.RUNNING,
    )
    db_session.add(scan_run)
    db_session.flush()
    return scan_run


def normalized_job(**overrides):
    payload = {
        "external_job_id": "123",
        "source_provider": "greenhouse",
        "source_url": "https://job-boards.greenhouse.io/acme/jobs/123",
        "canonical_url": "https://job-boards.greenhouse.io/acme/jobs/123",
        "application_url": "https://job-boards.greenhouse.io/acme/jobs/123",
        "title": "Senior Program Manager",
        "normalized_title": "senior program manager",
        "location": "Austin, TX",
        "normalized_location": "austin, tx",
        "department": "Operations",
        "employment_type": "Full-time",
        "description_text": "Role description",
        "description_hash": "hash-1",
        "provider_metadata": {"id": "123"},
        "source_payload_hash": "payload-1",
    }
    payload.update(overrides)
    return NormalizedJobPosting(**payload)


def test_first_scan_creates_new_jobs(db_session):
    company = make_company(db_session)
    scan_run = make_scan_run(db_session, company.id)
    service = JobIngestionService(JobRepository(db_session))

    result = service.ingest_company_jobs(
        company=company,
        normalized_jobs=[normalized_job()],
        scan_run=scan_run,
        authoritative=True,
    )

    job = db_session.query(JobPosting).one()
    assert result.created_count == 1
    assert job.review_status == ReviewStatus.NOT_REVIEWED
    assert job.career_site_status == CareerSiteStatus.ACTIVE


def test_second_identical_scan_creates_no_duplicates(db_session):
    company = make_company(db_session)
    scan_run = make_scan_run(db_session, company.id)
    service = JobIngestionService(JobRepository(db_session))
    service.ingest_company_jobs(
        company=company, normalized_jobs=[normalized_job()], scan_run=scan_run, authoritative=True
    )

    second_run = make_scan_run(db_session, company.id)
    result = service.ingest_company_jobs(
        company=company,
        normalized_jobs=[normalized_job()],
        scan_run=second_run,
        authoritative=True,
    )

    assert result.created_count == 0
    assert db_session.query(JobPosting).count() == 1


def test_modified_job_description_updates_existing_job(db_session):
    company = make_company(db_session)
    service = JobIngestionService(JobRepository(db_session))
    first_run = make_scan_run(db_session, company.id)
    service.ingest_company_jobs(
        company=company, normalized_jobs=[normalized_job()], scan_run=first_run, authoritative=True
    )

    second_run = make_scan_run(db_session, company.id)
    result = service.ingest_company_jobs(
        company=company,
        normalized_jobs=[
            normalized_job(
                description_text="Updated",
                description_hash="hash-2",
                source_payload_hash="payload-2",
            )
        ],
        scan_run=second_run,
        authoritative=True,
    )

    job = db_session.query(JobPosting).one()
    assert result.updated_count == 1
    assert job.job_description_hash == "hash-2"


def test_manual_review_and_notes_survive_repeated_scans(db_session):
    company = make_company(db_session)
    service = JobIngestionService(JobRepository(db_session))
    first_run = make_scan_run(db_session, company.id)
    service.ingest_company_jobs(
        company=company, normalized_jobs=[normalized_job()], scan_run=first_run, authoritative=True
    )
    job = db_session.query(JobPosting).one()
    job.review_status = ReviewStatus.APPLIED
    job.applied_at = datetime.now(UTC)
    job.user_notes = "Important role"

    second_run = make_scan_run(db_session, company.id)
    service.ingest_company_jobs(
        company=company, normalized_jobs=[normalized_job()], scan_run=second_run, authoritative=True
    )

    updated = db_session.query(JobPosting).one()
    assert updated.review_status == ReviewStatus.APPLIED
    assert updated.applied_at is not None
    assert updated.user_notes == "Important role"


def test_successful_scan_marks_absent_job_removed(db_session):
    company = make_company(db_session)
    service = JobIngestionService(JobRepository(db_session))
    first_run = make_scan_run(db_session, company.id)
    service.ingest_company_jobs(
        company=company, normalized_jobs=[normalized_job()], scan_run=first_run, authoritative=True
    )

    second_run = make_scan_run(db_session, company.id)
    result = service.ingest_company_jobs(
        company=company, normalized_jobs=[], scan_run=second_run, authoritative=True
    )

    job = db_session.query(JobPosting).one()
    assert result.marked_removed_count == 1
    assert job.career_site_status == CareerSiteStatus.REMOVED


def test_failed_or_incomplete_scan_does_not_mark_removed(db_session):
    company = make_company(db_session)
    service = JobIngestionService(JobRepository(db_session))
    first_run = make_scan_run(db_session, company.id)
    service.ingest_company_jobs(
        company=company, normalized_jobs=[normalized_job()], scan_run=first_run, authoritative=True
    )

    second_run = make_scan_run(db_session, company.id)
    result = service.ingest_company_jobs(
        company=company, normalized_jobs=[], scan_run=second_run, authoritative=False
    )

    job = db_session.query(JobPosting).one()
    assert result.marked_removed_count == 0
    assert job.career_site_status == CareerSiteStatus.ACTIVE


def test_removed_job_reappearing_becomes_active_again(db_session):
    company = make_company(db_session)
    service = JobIngestionService(JobRepository(db_session))
    first_run = make_scan_run(db_session, company.id)
    service.ingest_company_jobs(
        company=company, normalized_jobs=[normalized_job()], scan_run=first_run, authoritative=True
    )

    second_run = make_scan_run(db_session, company.id)
    service.ingest_company_jobs(
        company=company, normalized_jobs=[], scan_run=second_run, authoritative=True
    )
    third_run = make_scan_run(db_session, company.id)
    service.ingest_company_jobs(
        company=company, normalized_jobs=[normalized_job()], scan_run=third_run, authoritative=True
    )

    job = db_session.query(JobPosting).one()
    assert job.career_site_status == CareerSiteStatus.ACTIVE


def test_low_confidence_matches_are_not_auto_merged(db_session):
    company = make_company(db_session)
    scan_run = make_scan_run(db_session, company.id)
    service = JobIngestionService(JobRepository(db_session))
    service.ingest_company_jobs(
        company=company,
        normalized_jobs=[
            normalized_job(
                external_job_id=None,
                canonical_url=None,
                title="Program Manager",
                normalized_title="program manager",
                department="Ops",
            ),
            normalized_job(
                external_job_id=None,
                canonical_url=None,
                title="Program Manager",
                normalized_title="program manager",
                department="BizOps",
            ),
        ],
        scan_run=scan_run,
        authoritative=True,
    )

    assert db_session.query(JobPosting).count() == 2
