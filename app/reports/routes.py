from flask import render_template
from flask_login import login_required
from app.reports import reports_bp


@reports_bp.route('/reports')
@login_required
def index():
    """Placeholder reports index view."""
    return render_template('reports/index.html')
