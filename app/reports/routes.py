"""Reports Blueprint route controllers for monthly financial summaries and CSV export."""

import calendar
import csv
import io
from datetime import date
from decimal import Decimal
from flask import render_template, request, Response, abort
from flask_login import login_required, current_user
from sqlalchemy import func
from app.extensions import db
from app.models import Transaction, Category
from app.reports import reports_bp

MONTH_CHOICES = [
    (1, 'January'),
    (2, 'February'),
    (3, 'March'),
    (4, 'April'),
    (5, 'May'),
    (6, 'June'),
    (7, 'July'),
    (8, 'August'),
    (9, 'September'),
    (10, 'October'),
    (11, 'November'),
    (12, 'December'),
]


def validate_month_year(month_param, year_param):
    """Validate month and year query parameters.

    Returns (month, year, is_valid).
    If parameters are omitted, defaults to current month and year.
    If provided but invalid or out-of-range, returns (None, None, False).
    """
    today = date.today()
    if month_param is None and year_param is None:
        return today.month, today.year, True

    try:
        month = int(month_param) if month_param is not None else today.month
        year = int(year_param) if year_param is not None else today.year
        if not (1 <= month <= 12 and 2000 <= year <= 2100):
            return None, None, False
        return month, year, True
    except (ValueError, TypeError):
        return None, None, False


def sanitize_csv_cell(value):
    """Sanitize user-controlled text against spreadsheet formula injection (CSV Injection).

    If the string's first non-whitespace character begins with formula trigger characters
    ('=', '+', '-', '@', '\t', '\r'), prepend a single quote (') to force spreadsheet
    applications to interpret it strictly as a literal text cell.
    """
    if value is None:
        return ""
    str_val = str(value)
    stripped = str_val.lstrip()
    if stripped and stripped[0] in ('=', '+', '-', '@', '\t', '\r'):
        return "'" + str_val
    return str_val


@reports_bp.route('/reports', methods=['GET'])
@login_required
def index():
    """Render monthly financial report with KPIs, breakdown, largest expense, and transactions."""
    month_param = request.args.get('month')
    year_param = request.args.get('year')

    selected_month, selected_year, is_valid = validate_month_year(month_param, year_param)
    if not is_valid:
        abort(400, description="Invalid month or year parameter.")

    today = date.today()
    start_date = date(selected_year, selected_month, 1)
    last_day_num = calendar.monthrange(selected_year, selected_month)[1]
    end_date = date(selected_year, selected_month, last_day_num)
    month_name = calendar.month_name[selected_month]

    # 1. Total Income for selected month
    income_sum = (
        db.session.query(func.coalesce(func.sum(Transaction.amount), Decimal('0.00')))
        .join(Category)
        .filter(
            Transaction.user_id == current_user.id,
            Category.type == 'income',
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date
        )
        .scalar()
    )
    total_income = Decimal(str(income_sum))

    # 2. Total Expenses for selected month
    expense_sum = (
        db.session.query(func.coalesce(func.sum(Transaction.amount), Decimal('0.00')))
        .join(Category)
        .filter(
            Transaction.user_id == current_user.id,
            Category.type == 'expense',
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date
        )
        .scalar()
    )
    total_expenses = Decimal(str(expense_sum))

    # 3. Net Balance & Transaction Count
    net_balance = total_income - total_expenses
    total_tx_count = (
        Transaction.query.filter(
            Transaction.user_id == current_user.id,
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date
        ).count()
    )

    # 4. Category-Wise Expense Breakdown (sorted descending by spent amount)
    category_breakdown_raw = (
        db.session.query(
            Category.name,
            func.sum(Transaction.amount).label('total_amount')
        )
        .join(Category)
        .filter(
            Transaction.user_id == current_user.id,
            Category.type == 'expense',
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date
        )
        .group_by(Category.name)
        .order_by(func.sum(Transaction.amount).desc())
        .all()
    )

    category_breakdown = []
    for cat_name, cat_amount_sum in category_breakdown_raw:
        amount = Decimal(str(cat_amount_sum))
        if total_expenses > Decimal('0.00'):
            percentage = round(float((amount / total_expenses) * Decimal('100')), 1)
        else:
            percentage = 0.0
        category_breakdown.append({
            'name': cat_name,
            'amount': amount,
            'percentage': percentage
        })

    # 5. Largest Single Expense Transaction for the month
    largest_expense = (
        Transaction.query
        .join(Category)
        .filter(
            Transaction.user_id == current_user.id,
            Category.type == 'expense',
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date
        )
        .order_by(
            Transaction.amount.desc(),
            Transaction.transaction_date.desc(),
            Transaction.id.desc()
        )
        .first()
    )

    # 6. Monthly Transaction Ledger (both income and expenses, ordered newest first)
    transactions = (
        Transaction.query
        .filter(
            Transaction.user_id == current_user.id,
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date
        )
        .order_by(
            Transaction.transaction_date.desc(),
            Transaction.created_at.desc(),
            Transaction.id.desc()
        )
        .all()
    )

    available_years = list(range(today.year - 2, today.year + 3))

    return render_template(
        'reports/index.html',
        selected_month=selected_month,
        selected_year=selected_year,
        month_name=month_name,
        month_choices=MONTH_CHOICES,
        available_years=available_years,
        total_income=total_income,
        total_expenses=total_expenses,
        net_balance=net_balance,
        total_tx_count=total_tx_count,
        category_breakdown=category_breakdown,
        largest_expense=largest_expense,
        transactions=transactions
    )


@reports_bp.route('/reports/export', methods=['GET'])
@login_required
def export_csv():
    """Export selected month's transactions to CSV with formula injection protection."""
    month_param = request.args.get('month')
    year_param = request.args.get('year')

    selected_month, selected_year, is_valid = validate_month_year(month_param, year_param)
    if not is_valid:
        abort(400, description="Invalid month or year parameter.")

    start_date = date(selected_year, selected_month, 1)
    last_day_num = calendar.monthrange(selected_year, selected_month)[1]
    end_date = date(selected_year, selected_month, last_day_num)

    transactions = (
        Transaction.query
        .filter(
            Transaction.user_id == current_user.id,
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date
        )
        .order_by(
            Transaction.transaction_date.desc(),
            Transaction.created_at.desc(),
            Transaction.id.desc()
        )
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    # CSV Header
    writer.writerow([
        'Date',
        'Title',
        'Category',
        'Type',
        'Amount',
        'Payment Method',
        'Description'
    ])

    for tx in transactions:
        writer.writerow([
            tx.transaction_date.strftime('%Y-%m-%d'),
            sanitize_csv_cell(tx.title),
            sanitize_csv_cell(tx.category.name),
            tx.category.type.capitalize(),
            f"{tx.amount:.2f}",
            sanitize_csv_cell(tx.payment_method),
            sanitize_csv_cell(tx.description or '')
        ])

    csv_content = output.getvalue()
    filename = f"expense_tracker_report_{selected_year}_{selected_month:02d}.csv"

    return Response(
        csv_content,
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Content-Type': 'text/csv; charset=utf-8'
        }
    )
