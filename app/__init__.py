"""Application factory pattern implementation for Expense Tracker."""

import os
from flask import Flask, render_template
from dotenv import load_dotenv
from app.extensions import db, login_manager, csrf

# Load environment variables from .env file
load_dotenv()


def create_app(config_override=None):
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__, instance_relative_config=True)

    # Ensure the instance directory exists for SQLite database storage
    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError:
        pass

    # Default application configuration
    default_db_path = os.path.join(app.instance_path, 'expense_tracker.db')
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev-secret-key-expense-tracker-2026'),
        SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URL', f'sqlite:///{default_db_path}'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    # Apply configuration overrides (e.g. for testing)
    if config_override:
        app.config.update(config_override)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Configure Flask-Login
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return db.session.get(User, int(user_id))

    # Register Blueprints
    from app.auth import auth_bp
    from app.main import main_bp
    from app.transactions import transactions_bp
    from app.budgets import budgets_bp
    from app.reports import reports_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(transactions_bp)
    app.register_blueprint(budgets_bp)
    app.register_blueprint(reports_bp)

    # Register custom Jinja template filters
    from app.utils import format_inr
    app.jinja_env.filters['inr'] = format_inr
    app.jinja_env.filters['currency'] = format_inr
    app.jinja_env.globals['format_inr'] = format_inr

    # Register application error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    return app
