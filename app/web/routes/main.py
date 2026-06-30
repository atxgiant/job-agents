from __future__ import annotations

from flask import Blueprint, current_app, jsonify, render_template

from app.services.candidate_profile import CandidateProfileService
from app.services.dashboard import DashboardService

main_bp = Blueprint("main", __name__)


@main_bp.get("/")
def dashboard():
    stats = DashboardService().get_stats()
    profile = CandidateProfileService().load()
    return render_template(
        "dashboard.html",
        stats=stats,
        profile=profile,
        config=current_app.config["HEAD_HUNTER"],
    )


@main_bp.get("/health")
def health():
    profile = CandidateProfileService().load()
    return jsonify(
        {
            "status": "ok",
            "candidate_profile_hash": profile.content_hash,
            "candidate_profile_path": str(profile.source_path),
        }
    )
