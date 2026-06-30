from __future__ import annotations

from datetime import UTC, datetime

from app.models import Company, JobPosting
from app.models.enums import CareerSiteStatus, CompanyStatus, CompanyType, ReviewStatus
from app.repositories.job_repository import JobRepository
from app.services.job_review import JobReviewService
from app.web.app import create_app


def seed_jobs(db_session):
    company = Company(
        name="Acme Robotics",
        normalized_name="acme robotics",
        company_type=CompanyType.PUBLIC,
        status=CompanyStatus.ACTIVE,
    )
    db_session.add(company)
    db_session.flush()
    now = datetime.now(UTC)
    jobs = [
        JobPosting(
            company_id=company.id,
            source_provider="greenhouse",
            source_url="https://example.com/1",
            canonical_url="https://example.com/1",
            title="Role 1",
            normalized_title="role 1",
            first_seen_at=now,
            last_seen_at=now,
            last_verified_at=now,
            career_site_status=CareerSiteStatus.ACTIVE,
            career_site_status_changed_at=now,
            review_status=ReviewStatus.NOT_REVIEWED,
        ),
        JobPosting(
            company_id=company.id,
            source_provider="greenhouse",
            source_url="https://example.com/2",
            canonical_url="https://example.com/2",
            title="Role 2",
            normalized_title="role 2",
            first_seen_at=now,
            last_seen_at=now,
            last_verified_at=now,
            career_site_status=CareerSiteStatus.ACTIVE,
            career_site_status_changed_at=now,
            review_status=ReviewStatus.REJECTED,
        ),
        JobPosting(
            company_id=company.id,
            source_provider="greenhouse",
            source_url="https://example.com/3",
            canonical_url="https://example.com/3",
            title="Role 3",
            normalized_title="role 3",
            first_seen_at=now,
            last_seen_at=now,
            last_verified_at=now,
            career_site_status=CareerSiteStatus.ACTIVE,
            career_site_status_changed_at=now,
            review_status=ReviewStatus.APPLIED,
        ),
    ]
    db_session.add_all(jobs)
    db_session.commit()
    return company, jobs


def test_default_queue_excludes_rejected_and_applied(db_session, monkeypatch):
    seed_jobs(db_session)
    monkeypatch.setattr("app.web.routes.opportunities.get_session", lambda: db_session)
    app = create_app()
    client = app.test_client()

    response = client.get("/opportunities/")

    assert b"Role 1" in response.data
    assert b"Role 2" not in response.data
    assert b"Role 3" not in response.data


def test_filtered_view_can_include_rejected_and_applied(db_session, monkeypatch):
    seed_jobs(db_session)
    monkeypatch.setattr("app.web.routes.opportunities.get_session", lambda: db_session)
    app = create_app()
    client = app.test_client()

    response = client.get("/opportunities/?active_view=all&review_status=rejected")

    assert b"Role 2" in response.data


def test_manual_review_actions_create_history_records(db_session):
    _, jobs = seed_jobs(db_session)
    service = JobReviewService(JobRepository(db_session))

    service.update_review_status(jobs[0].id, new_status=ReviewStatus.INTERESTED)
    db_session.commit()
    history = JobRepository(db_session).list_job_history(jobs[0].id)

    assert history[0].event_type == "review_status_changed"


def test_job_csv_export_includes_expected_fields(db_session):
    _, jobs = seed_jobs(db_session)
    monkeypatch_session = db_session
    exported = JobRepository(monkeypatch_session).list_jobs_for_export()
    first = exported[0]
    assert hasattr(first, "source_url")
    assert hasattr(first, "application_url")
