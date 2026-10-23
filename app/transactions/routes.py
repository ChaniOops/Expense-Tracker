from flask import render_template
from flask_login import login_required
from app.transactions import transactions_bp


@transactions_bp.route('/transactions')
@login_required
def index():
    """Placeholder transactions index view."""
    return render_template('transactions/index.html')
