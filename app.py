import os
import socket
from flask import Flask

from config import config_map
from extensions import db, login_manager, mail, migrate
from models import Member

# Global safety net: without this, a slow/unreachable network service
# (email server, SMS API, anything) can hang a request indefinitely —
# and Gunicorn's worker-timeout watchdog then kills the whole worker
# mid-request, which looks like a random crash rather than a normal,
# catchable error. This caps EVERY socket operation app-wide at 10
# seconds, so a hang becomes a normal Python exception your try/except
# blocks can actually catch.
socket.setdefaulttimeout(10)


def create_app():
    app = Flask(__name__)

    env = os.environ.get("FLASK_ENV", "production")
    app.config.from_object(config_map.get(env, config_map["production"]))

    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)

    with app.app_context():
        db.create_all()

    @login_manager.user_loader
    def load_user(user_id):
        return Member.query.get(int(user_id))

    from routes.public import public_bp
    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.admin import admin_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(admin_bp)

  # ============================================================
# REPLACE the existing @app.route("/healthz") block in app.py
# with this version — it now also reports which database engine
# is actually active, without exposing the password or host.
# ============================================================

    @app.route("/healthz")
    def healthz():
        db_url = app.config.get("SQLALCHEMY_DATABASE_URI", "")
        engine = db_url.split("://")[0] if "://" in db_url else "unknown"
        return {
            "status": "ok",
            "database_engine": engine,  # should say "postgresql" — if it says "sqlite", that's the bug
        }


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
