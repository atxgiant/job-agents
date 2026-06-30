from __future__ import annotations

from flask import (
    Blueprint,
    Response,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from app.config.settings import load_runtime_config
from app.models.enums import CompanyStatus, CompanyType
from app.repositories.company_repository import CompanyFilters
from app.repositories.db import get_session
from app.services.company_registry import CompanyLifecycleError, CompanyRegistryService

company_bp = Blueprint("companies", __name__, url_prefix="/companies")


def _filters_from_request() -> CompanyFilters:
    return CompanyFilters(
        search=request.args.get("search", ""),
        status=request.args.get("status", ""),
        scan_block=request.args.get("scan_block", ""),
        company_type=request.args.get("company_type", ""),
        industry_tag=request.args.get("industry_tag", ""),
        seed_source=request.args.get("seed_source", ""),
        ticker=request.args.get("ticker", ""),
    )


def _company_payload_from_form() -> dict[str, str]:
    return {
        "name": request.form.get("name", ""),
        "website_url": request.form.get("website_url", ""),
        "careers_url": request.form.get("careers_url", ""),
        "ats_provider": request.form.get("ats_provider", ""),
        "ats_company_identifier": request.form.get("ats_company_identifier", ""),
        "company_type": request.form.get("company_type", CompanyType.UNKNOWN.value),
        "public_status": request.form.get("public_status", ""),
        "ticker": request.form.get("ticker", ""),
        "industry_tags": request.form.get("industry_tags", ""),
        "product_tags": request.form.get("product_tags", ""),
        "company_description": request.form.get("company_description", ""),
        "headquarters_location": request.form.get("headquarters_location", ""),
        "status": request.form.get("status", CompanyStatus.ACTIVE.value),
        "scan_block": request.form.get("scan_block", ""),
        "scan_frequency_override": request.form.get("scan_frequency_override", ""),
        "seed_source": request.form.get("seed_source", ""),
        "seed_run_id": request.form.get("seed_run_id", ""),
        "seed_rationale": request.form.get("seed_rationale", ""),
        "source_urls": request.form.get("source_urls", ""),
        "rejection_reason": request.form.get("rejection_reason", ""),
        "exclusion_reason": request.form.get("exclusion_reason", ""),
        "aliases": request.form.get("aliases", ""),
    }


@company_bp.get("/")
def list_companies():
    filters = _filters_from_request()
    config = load_runtime_config()
    with get_session() as session:
        service = CompanyRegistryService(session)
        companies = service.list_companies(filters)
    return render_template(
        "companies/list.html",
        companies=companies,
        filters=filters,
        statuses=list(CompanyStatus),
        company_types=list(CompanyType),
        total_scan_blocks=config.scan_policy.total_scan_blocks,
        import_report=None,
        export_query=request.query_string.decode(),
    )


@company_bp.get("/new")
def new_company():
    return render_template(
        "companies/form.html",
        company=None,
        statuses=list(CompanyStatus),
        company_types=list(CompanyType),
    )


@company_bp.post("/")
def create_company():
    payload = _company_payload_from_form()
    with get_session() as session:
        service = CompanyRegistryService(session)
        try:
            company = service.create_company(payload=payload)
        except CompanyLifecycleError as exc:
            flash(str(exc), "danger")
            return render_template(
                "companies/form.html",
                company=None,
                form_data=payload,
                statuses=list(CompanyStatus),
                company_types=list(CompanyType),
            ), 400
    flash(f"Created company {company.name}.", "success")
    return redirect(url_for("companies.company_detail", company_id=company.id))


@company_bp.get("/<int:company_id>")
def company_detail(company_id: int):
    with get_session() as session:
        service = CompanyRegistryService(session)
        company = service.get_company(company_id)
        audit_events = service.company_audit_timeline(company_id)
    return render_template(
        "companies/detail.html",
        company=company,
        audit_events=audit_events,
        statuses=list(CompanyStatus),
        company_types=list(CompanyType),
    )


@company_bp.get("/<int:company_id>/edit")
def edit_company(company_id: int):
    with get_session() as session:
        service = CompanyRegistryService(session)
        company = service.get_company(company_id)
    return render_template(
        "companies/form.html",
        company=company,
        statuses=list(CompanyStatus),
        company_types=list(CompanyType),
    )


@company_bp.post("/<int:company_id>/edit")
def update_company(company_id: int):
    payload = _company_payload_from_form()
    with get_session() as session:
        service = CompanyRegistryService(session)
        try:
            service.update_company(company_id=company_id, payload=payload)
        except CompanyLifecycleError as exc:
            flash(str(exc), "danger")
            company = service.get_company(company_id)
            return render_template(
                "companies/form.html",
                company=company,
                form_data=payload,
                statuses=list(CompanyStatus),
                company_types=list(CompanyType),
            ), 400
    flash("Company updated.", "success")
    return redirect(url_for("companies.company_detail", company_id=company_id))


@company_bp.post("/<int:company_id>/activate")
def activate_company(company_id: int):
    with get_session() as session:
        CompanyRegistryService(session).activate_company(company_id)
    flash("Company activated.", "success")
    return redirect(url_for("companies.company_detail", company_id=company_id))


@company_bp.post("/<int:company_id>/deactivate")
def deactivate_company(company_id: int):
    with get_session() as session:
        CompanyRegistryService(session).deactivate_company(company_id)
    flash("Company deactivated.", "warning")
    return redirect(url_for("companies.company_detail", company_id=company_id))


@company_bp.post("/<int:company_id>/reject")
def reject_company(company_id: int):
    reason = request.form.get("reason", "")
    with get_session() as session:
        try:
            CompanyRegistryService(session).reject_company(company_id, reason)
        except CompanyLifecycleError as exc:
            flash(str(exc), "danger")
            return redirect(url_for("companies.company_detail", company_id=company_id))
    flash("Company rejected.", "warning")
    return redirect(url_for("companies.company_detail", company_id=company_id))


@company_bp.post("/<int:company_id>/exclude")
def exclude_company(company_id: int):
    reason = request.form.get("reason", "")
    with get_session() as session:
        try:
            CompanyRegistryService(session).exclude_company(company_id, reason)
        except CompanyLifecycleError as exc:
            flash(str(exc), "danger")
            return redirect(url_for("companies.company_detail", company_id=company_id))
    flash("Company excluded.", "warning")
    return redirect(url_for("companies.company_detail", company_id=company_id))


@company_bp.post("/<int:company_id>/reactivate")
def reactivate_company(company_id: int):
    with get_session() as session:
        CompanyRegistryService(session).reactivate_company(company_id)
    flash("Company reactivated.", "success")
    return redirect(url_for("companies.company_detail", company_id=company_id))


@company_bp.post("/<int:company_id>/scan-block")
def assign_scan_block(company_id: int):
    raw_value = request.form.get("scan_block", "").strip()
    scan_block = int(raw_value) if raw_value else None
    with get_session() as session:
        CompanyRegistryService(session).assign_scan_block(company_id, scan_block)
    flash("Scan block updated.", "success")
    return redirect(url_for("companies.company_detail", company_id=company_id))


@company_bp.get("/rebalance-preview")
def rebalance_preview():
    config = load_runtime_config()
    with get_session() as session:
        previews = CompanyRegistryService(session).preview_rebalance(
            total_blocks=config.scan_policy.total_scan_blocks
        )
    return render_template(
        "companies/rebalance_preview.html",
        previews=previews,
        total_scan_blocks=config.scan_policy.total_scan_blocks,
    )


@company_bp.post("/rebalance")
def rebalance():
    config = load_runtime_config()
    with get_session() as session:
        previews = CompanyRegistryService(session).rebalance_scan_blocks(
            total_blocks=config.scan_policy.total_scan_blocks
        )
    flash(f"Rebalanced {len(previews)} automatically assigned companies.", "success")
    return redirect(url_for("companies.list_companies"))


@company_bp.post("/import")
def import_companies():
    upload = request.files.get("csv_file")
    if not upload or not upload.filename:
        flash("Choose a CSV file to import.", "danger")
        return redirect(url_for("companies.list_companies"))
    csv_text = upload.read().decode("utf-8")
    filters = _filters_from_request()
    config = load_runtime_config()
    with get_session() as session:
        service = CompanyRegistryService(session)
        report = service.import_companies_csv(csv_text)
        companies = service.list_companies(filters)
    return render_template(
        "companies/list.html",
        companies=companies,
        filters=filters,
        statuses=list(CompanyStatus),
        company_types=list(CompanyType),
        total_scan_blocks=config.scan_policy.total_scan_blocks,
        import_report=report,
        export_query=request.query_string.decode(),
    )


@company_bp.get("/export")
def export_companies():
    filters = _filters_from_request()
    selected_ids = {
        int(value) for value in request.args.getlist("company_id") if value.strip().isdigit()
    }
    with get_session() as session:
        csv_text = CompanyRegistryService(session).export_companies_csv(
            filters, selected_ids or None
        )
    return Response(
        csv_text,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=companies.csv"},
    )
