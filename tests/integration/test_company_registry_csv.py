from app.models.enums import CompanyStatus
from app.services.company_registry import CompanyRegistryService

CSV_TEXT = (
    "name,website_url,careers_url,ats_provider,ats_company_identifier,company_type,"
    "public_status,ticker,industry_tags,product_tags,company_description,"
    "headquarters_location,status,scan_block,scan_frequency_override,seed_source,"
    "seed_run_id,seed_rationale,source_urls,rejection_reason,exclusion_reason,aliases\n"
    "Acme Robotics,https://acme.example,https://acme.example/careers,greenhouse,acme,public,public,ACME,"
    '"robotics, logistics","devices, mobility",Robotics company,Austin,active,2,,seed,run-1,why,'
    "https://source.example,,,Acme\n"
)


def test_csv_import_is_idempotent(db_session):
    service = CompanyRegistryService(db_session)

    first = service.import_companies_csv(CSV_TEXT)
    second = service.import_companies_csv(CSV_TEXT)
    companies = service.list_companies()

    assert first.created == 1
    assert second.updated == 1
    assert len(companies) == 1


def test_csv_import_does_not_silently_reactivate_rejected_company(db_session):
    service = CompanyRegistryService(db_session)
    company = service.create_company(name="Acme Robotics", status="active")
    service.reject_company(company.id, "No fit")

    report = service.import_companies_csv(CSV_TEXT)
    updated_company = service.get_company(company.id)

    assert report.updated == 1
    assert updated_company.status == CompanyStatus.REJECTED


def test_export_includes_status_provenance_and_reasons(db_session):
    service = CompanyRegistryService(db_session)
    service.create_company(
        name="Acme Robotics",
        status="excluded",
        exclusion_reason="Blocked by policy",
        seed_source="seed",
        seed_run_id="run-1",
    )

    csv_text = service.export_companies_csv()

    assert "status" in csv_text
    assert "excluded" in csv_text
    assert "Blocked by policy" in csv_text
    assert "run-1" in csv_text


def test_audit_records_exist_for_lifecycle_actions(db_session):
    service = CompanyRegistryService(db_session)
    company = service.create_company(name="Acme Robotics", status="active")
    service.deactivate_company(company.id)
    service.activate_company(company.id)
    service.exclude_company(company.id, "Blocked")
    service.reactivate_company(company.id)

    audit_events = service.company_audit_timeline(company.id)
    event_types = {event.event_type for event in audit_events}

    assert "company_created" in event_types
    assert "company_deactivated" in event_types
    assert "company_activated" in event_types
    assert "company_excluded" in event_types
    assert "company_reactivated" in event_types
