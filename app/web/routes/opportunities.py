from __future__ import annotations

from datetime import UTC, datetime

from flask import Blueprint, Response, flash, redirect, render_template, request, url_for

from app.models.enums import CareerSiteStatus, ReviewStatus
from app.repositories.company_repository import CompanyRepository
from app.repositories.db import get_session
from app.repositories.job_repository import JobRepository, OpportunityFilters
from app.services.job_review import JobReviewError, JobReviewService

opportunity_bp = Blueprint("opportunities", __name__, url_prefix="/opportunities")


def _filters_from_request() -> OpportunityFilters:
    return OpportunityFilters(
        company_id=request.args.get("company_id", ""),
        review_status=request.args.get("review_status", ""),
        career_site_status=request.args.get("career_site_status", ""),
        location=request.args.get("location", ""),
        department=request.args.get("department", ""),
        source_provider=request.args.get("source_provider", ""),
        first_seen_from=request.args.get("first_seen_from", ""),
        first_seen_to=request.args.get("first_seen_to", ""),
        last_verified_from=request.args.get("last_verified_from", ""),
        last_verified_to=request.args.get("last_verified_to", ""),
        active_view=request.args.get("active_view", "queue"),
    )


@opportunity_bp.get("/")
def list_opportunities():
    filters = _filters_from_request()
    with get_session() as session:
        jobs = JobRepository(session).list_opportunities(filters)
        companies = CompanyRepository(session).list_companies()
    return render_template(
        "opportunities/list.html",
        jobs=jobs,
        companies=companies,
        filters=filters,
        review_statuses=list(ReviewStatus),
        career_site_statuses=list(CareerSiteStatus),
        export_query=request.query_string.decode(),
    )


@opportunity_bp.get("/<int:job_id>")
def opportunity_detail(job_id: int):
    with get_session() as session:
        repo = JobRepository(session)
        job = repo.get_job(job_id)
        if not job:
            flash("Job not found.", "danger")
            return redirect(url_for("opportunities.list_opportunities"))
        observations = repo.list_job_observations(job_id)
        history = repo.list_job_history(job_id)
    return render_template(
        "opportunities/detail.html",
        job=job,
        observations=observations,
        history=history,
        review_statuses=list(ReviewStatus),
    )


@opportunity_bp.post("/<int:job_id>/status")
def update_opportunity_status(job_id: int):
    raw_status = request.form.get("review_status", ReviewStatus.NOT_REVIEWED.value)
    reason = request.form.get("reason", "") or None
    applied_date = request.form.get("applied_at", "").strip()
    applied_at = None
    if applied_date:
        applied_at = datetime.fromisoformat(applied_date).replace(tzinfo=UTC)
    with get_session() as session:
        service = JobReviewService(JobRepository(session))
        try:
            service.update_review_status(
                job_id,
                new_status=ReviewStatus(raw_status),
                reason=reason,
                applied_at=applied_at,
            )
            session.commit()
        except JobReviewError as exc:
            session.rollback()
            flash(str(exc), "danger")
            return redirect(url_for("opportunities.opportunity_detail", job_id=job_id))
    flash("Job review status updated.", "success")
    return redirect(url_for("opportunities.opportunity_detail", job_id=job_id))


@opportunity_bp.post("/<int:job_id>/notes")
def update_opportunity_notes(job_id: int):
    notes = request.form.get("user_notes", "")
    with get_session() as session:
        service = JobReviewService(JobRepository(session))
        try:
            service.update_notes(job_id, notes)
            session.commit()
        except JobReviewError as exc:
            session.rollback()
            flash(str(exc), "danger")
            return redirect(url_for("opportunities.opportunity_detail", job_id=job_id))
    flash("Notes updated.", "success")
    return redirect(url_for("opportunities.opportunity_detail", job_id=job_id))


@opportunity_bp.get("/export")
def export_opportunities():
    filters = _filters_from_request()
    selected_ids = {
        int(value) for value in request.args.getlist("job_id") if value.strip().isdigit()
    }
    with get_session() as session:
        jobs = JobRepository(session).list_jobs_for_export(filters, selected_ids or None)
    header = (
        "company_name,title,location,department,employment_type,review_status,career_site_status,"
        "first_seen_at,last_seen_at,last_verified_at,source_provider,source_url,application_url,"
        "user_notes,rejection_reason,applied_at\n"
    )
    rows = []
    for job in jobs:
        rows.append(
            ",".join(
                [
                    f'"{(job.company.name or "").replace(chr(34), chr(39))}"',
                    f'"{(job.title or "").replace(chr(34), chr(39))}"',
                    f'"{(job.location or "").replace(chr(34), chr(39))}"',
                    f'"{(job.department or "").replace(chr(34), chr(39))}"',
                    f'"{(job.employment_type or "").replace(chr(34), chr(39))}"',
                    job.review_status.value,
                    job.career_site_status.value,
                    job.first_seen_at.isoformat(),
                    job.last_seen_at.isoformat(),
                    job.last_verified_at.isoformat(),
                    job.source_provider or "",
                    job.source_url or "",
                    job.application_url or "",
                    f'"{(job.user_notes or "").replace(chr(34), chr(39))}"',
                    f'"{(job.rejection_reason or "").replace(chr(34), chr(39))}"',
                    job.applied_at.isoformat() if job.applied_at else "",
                ]
            )
        )
    csv_text = header + "\n".join(rows) + ("\n" if rows else "")
    return Response(
        csv_text,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=opportunities.csv"},
    )
