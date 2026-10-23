from flask import render_template
from flask_login import login_required
from app.budgets import budgets_bp


@budgets_bp.route('/budgets')
@login_required
def index():
    """Placeholder budgets index view."""
    return render_template('budgets/index.html')
