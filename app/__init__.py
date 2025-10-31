import os
from datetime import datetime
from typing import Dict

from flask import Flask, redirect, session, url_for

from . import db


DIAMETER_SPEEDS: Dict[int, float] = {
    50: 17.0,
    63: 17.0,
    75: 17.0,
    90: 15.0,
    110: 7.0,
    125: 5.0,
    140: 3.5,
    160: 2.25,
    200: 1.8,
}

SHIFT_INFO = {
    1: {"label": "1. Vardiya", "start": "07:30", "end": "15:30"},
    2: {"label": "2. Vardiya", "start": "15:30", "end": "23:30"},
    3: {"label": "3. Vardiya", "start": "23:30", "end": "07:30"},
}

ACTIVE_MINUTES_PER_SHIFT = 420


def create_app() -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("FLASK_SECRET_KEY", "dev-secret-key"),
        DATABASE=os.path.join(app.instance_path, "akona.sqlite"),
        PERMANENT_SESSION_LIFETIME=60 * 60 * 8,
    )

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)

    @app.before_request
    def require_login() -> None:
        from flask import request

        if request.endpoint in {"main.login", "static"}:
            return
        if session.get("user_id") is None:
            return redirect(url_for("main.login"))

    from .views import bp

    app.register_blueprint(bp)

    @app.context_processor
    def inject_globals() -> Dict[str, object]:
        return {
            "diameter_speeds": DIAMETER_SPEEDS,
            "shift_info": SHIFT_INFO,
            "active_minutes": ACTIVE_MINUTES_PER_SHIFT,
            "current_year": datetime.utcnow().year,
        }

    with app.app_context():
        db.init_db()

    return app
