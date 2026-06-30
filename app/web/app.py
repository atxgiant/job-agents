from __future__ import annotations

from flask import Flask

from app.config.settings import load_runtime_config
from app.web.routes.companies import company_bp
from app.web.routes.main import main_bp


def create_app() -> Flask:
    config = load_runtime_config()
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["SECRET_KEY"] = config.flask_secret_key
    app.config["HEAD_HUNTER"] = config.model_dump()
    app.register_blueprint(main_bp)
    app.register_blueprint(company_bp)
    return app
