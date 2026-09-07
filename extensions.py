"""
Shared extension instances, created here (not in app.py) so blueprints and
models can import them without circular imports.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate

db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()
migrate = Migrate()

login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to access your dashboard."
login_manager.login_message_category = "info"
