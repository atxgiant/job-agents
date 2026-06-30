from __future__ import annotations

from datetime import UTC, datetime

from flask import Flask

from app.config.settings import load_runtime_config
from app.web.routes.companies import company_bp
from app.web.routes.main import main_bp
from app.web.routes.opportunities import opportunity_bp


def create_app() -> Flask:
    config = load_runtime_config()
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["SECRET_KEY"] = config.flask_secret_key
    app.config["HEAD_HUNTER"] = config.model_dump()
    app.add_template_filter(_relative_age, "relative_age")
    app.register_blueprint(main_bp)
    app.register_blueprint(company_bp)
    app.register_blueprint(opportunity_bp)
    return app


def _relative_age(value):
    if not value:
        return "—"
    now = datetime.now(UTC)
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    delta = now - value
    days = delta.days
    if days > 0:
        return f"{days}d ago"
    hours = delta.seconds // 3600
    if hours > 0:
        return f"{hours}h ago"
    minutes = delta.seconds // 60
    return f"{minutes}m ago"
