from app.models.enums import CompanyStatus
from app.services.company_registry import CompanyLifecycleError, CompanyRegistryService


def create_sample_company(service: CompanyRegistryService, **overrides):
    name = overrides.get("name", "Acme Robotics")
    payload = {
        "name": name,
        "website_url": f"https://{name.lower().replace(' ', '-')}.example",
        "company_type": "public",
        "status": "active",
        "industry_tags": "robotics, logistics",
    }
    payload.update(overrides)
    return service.create_company(**payload)


def test_rejecting_company_requires_reason(db_session):
    service = CompanyRegistryService(db_session)
    company = create_sample_company(service)

    try:
        service.reject_company(company.id, "")
    except CompanyLifecycleError as exc:
        assert "requires a rejection reason" in str(exc)
    else:
        raise AssertionError("Expected CompanyLifecycleError")


def test_excluding_company_requires_reason(db_session):
    service = CompanyRegistryService(db_session)
    company = create_sample_company(service)

    try:
        service.exclude_company(company.id, "")
    except CompanyLifecycleError as exc:
        assert "requires an exclusion reason" in str(exc)
    else:
        raise AssertionError("Expected CompanyLifecycleError")


def test_rejected_company_stays_rejected_through_seed_upsert(db_session):
    service = CompanyRegistryService(db_session)
    company = create_sample_company(service)
    service.reject_company(company.id, "Not a fit")

    existing, outcome = service.upsert_seed_candidate(
        name="Acme Robotics",
        website_url="https://acme.example",
        ticker=None,
        seed_source="test_seed",
    )

    assert outcome == "blocked_rejected"
    assert existing.status == CompanyStatus.REJECTED


def test_explicit_reactivation_works_and_is_audited(db_session):
    service = CompanyRegistryService(db_session)
    company = create_sample_company(service)
    service.reject_company(company.id, "Not a fit")

    company = service.reactivate_company(company.id)
    audit_events = service.company_audit_timeline(company.id)

    assert company.status == CompanyStatus.ACTIVE
    assert audit_events[0].event_type == "company_reactivated"


def test_invalid_activation_of_rejected_company_fails(db_session):
    service = CompanyRegistryService(db_session)
    company = create_sample_company(service)
    service.reject_company(company.id, "Not a fit")

    try:
        service.activate_company(company.id)
    except CompanyLifecycleError as exc:
        assert "explicit reactivation" in str(exc)
    else:
        raise AssertionError("Expected CompanyLifecycleError")


def test_inactive_rejected_and_excluded_companies_omitted_from_scan_assignment(db_session):
    service = CompanyRegistryService(db_session)
    active = create_sample_company(service, name="Active Co")
    inactive = create_sample_company(service, name="Inactive Co", status="inactive")
    rejected = create_sample_company(
        service,
        name="Rejected Co",
        status="rejected",
        rejection_reason="No fit",
    )
    excluded = create_sample_company(
        service,
        name="Excluded Co",
        status="excluded",
        exclusion_reason="Policy block",
    )

    previews = service.preview_rebalance(total_blocks=7)

    assert {preview.company_id for preview in previews} == {active.id}
    assert inactive.id not in {preview.company_id for preview in previews}
    assert rejected.id not in {preview.company_id for preview in previews}
    assert excluded.id not in {preview.company_id for preview in previews}


def test_manual_scan_block_assignments_survive_rebalance(db_session):
    service = CompanyRegistryService(db_session)
    manual = create_sample_company(service, name="Manual Co")
    auto = create_sample_company(service, name="Auto Co")
    service.assign_scan_block(manual.id, 6)

    previews = service.rebalance_scan_blocks(total_blocks=3)
    manual_after = service.get_company(manual.id)
    auto_after = service.get_company(auto.id)

    assert manual_after.scan_block == 6
    assert manual_after.scan_assignment_mode == "manual"
    assert auto_after.scan_block in {0, 1, 2}
    assert any(preview.company_id == auto.id for preview in previews)


def test_automatic_assignments_distribute_companies_reasonably(db_session):
    service = CompanyRegistryService(db_session)
    for index in range(8):
        create_sample_company(service, name=f"Company {index}")

    previews = service.rebalance_scan_blocks(total_blocks=3)
    assignments = [preview.proposed_block for preview in previews]

    assert assignments.count(0) == 3
    assert assignments.count(1) == 3
    assert assignments.count(2) == 2
