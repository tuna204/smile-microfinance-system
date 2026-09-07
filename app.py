import os
from flask import Flask

from config import config_map
from extensions import db, login_manager, mail, migrate
from models import Member


def create_app():
    app = Flask(__name__)

    env = os.environ.get("FLASK_ENV", "production")
    app.config.from_object(config_map.get(env, config_map["production"]))

    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)

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

    @app.route("/healthz")
    def healthz():
        return {"status": "ok"}

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
