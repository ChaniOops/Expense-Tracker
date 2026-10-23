from flask import Blueprint

budgets_bp = Blueprint('budgets', __name__)

from app.budgets import routes  # noqa: E402, F401
