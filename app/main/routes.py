"""Main Blueprint route controllers for Dashboard analytics and KPIs."""

import calendar
from datetime import date
from decimal import Decimal
from flask import render_template
from flask_login import login_required, current_user
from sqlalchemy import func
from app.extensions import db
from app.models import Transaction, Category, Budget
from app.main import main_bp


def get_last_6_months(ref_date=None):
    """Return list of (first_day, last_day, label) for the last 6 calendar months in chronological order."""
    if ref_date is None:
        ref_date = date.today()

    months = []
    year = ref_date.year
    month = ref_date.month

    for i in range(5, -1, -1):
        target_month = month - i
        target_year = year
        while target_month <= 0:
            target_month += 12
            target_year -= 1

        first_day = date(target_year, target_month, 1)
        last_day_num = calendar.monthrange(target_year, target_month)[1]
        last_day = date(target_year, target_month, last_day_num)
        label = first_day.strftime('%b %Y')

        months.append((first_day, last_day, label))

    return months


@main_bp.route('/')
@login_required
def index():
    """Render dashboard summary cards, recent transactions, and Chart.js analytics."""
    today = date.today()
    start_of_month = date(today.year, today.month, 1)
    last_day_num = calendar.monthrange(today.year, today.month)[1]
    end_of_month = date(today.year, today.month, last_day_num)
    current_month_name = today.strftime('%B %Y')

    # 1. Current Month Income Total
    income_sum = (
        db.session.query(func.coalesce(func.sum(Transaction.amount), Decimal('0.00')))
        .join(Category)
        .filter(
            Transaction.user_id == current_user.id,
            Category.type == 'income',
            Transaction.transaction_date >= start_of_month,
            Transaction.transaction_date <= end_of_month
        )
        .scalar()
    )
    monthly_income = Decimal(str(income_sum))

    # 2. Current Month Expense Total
    expense_sum = (
        db.session.query(func.coalesce(func.sum(Transaction.amount), Decimal('0.00')))
        .join(Category)
        .filter(
            Transaction.user_id == current_user.id,
            Category.type == 'expense',
            Transaction.transaction_date >= start_of_month,
            Transaction.transaction_date <= end_of_month
        )
        .scalar()
    )
    monthly_expenses = Decimal(str(expense_sum))

    # 3. Net Balance & Transaction Count
    net_balance = monthly_income - monthly_expenses
    monthly_tx_count = (
        Transaction.query.filter(
            Transaction.user_id == current_user.id,
            Transaction.transaction_date >= start_of_month,
            Transaction.transaction_date <= end_of_month
        ).count()
    )

    # 4. Recent Transactions (Latest 5 records)
    recent_transactions = (
        Transaction.query.filter_by(user_id=current_user.id)
        .order_by(Transaction.transaction_date.desc(), Transaction.created_at.desc(), Transaction.id.desc())
        .limit(5)
        .all()
    )

    # 5. Expense Breakdown by Category (Current Month)
    category_expenses = (
        db.session.query(Category.name, func.sum(Transaction.amount))
        .join(Category)
        .filter(
            Transaction.user_id == current_user.id,
            Category.type == 'expense',
            Transaction.transaction_date >= start_of_month,
            Transaction.transaction_date <= end_of_month
        )
        .group_by(Category.name)
        .order_by(func.sum(Transaction.amount).desc())
        .all()
    )
    category_labels = [row[0] for row in category_expenses]
    category_amounts = [float(row[1]) for row in category_expenses]
    has_expenses = bool(monthly_expenses > 0 and len(category_amounts) > 0)

    # 6. Six-Month Cash Flow Trend (Last 6 Calendar Months)
    six_months = get_last_6_months(today)
    monthly_labels = []
    six_month_income = []
    six_month_expense = []

    for first_d, last_d, label in six_months:
        monthly_labels.append(label)

        inc = (
            db.session.query(func.coalesce(func.sum(Transaction.amount), Decimal('0.00')))
            .join(Category)
            .filter(
                Transaction.user_id == current_user.id,
                Category.type == 'income',
                Transaction.transaction_date >= first_d,
                Transaction.transaction_date <= last_d
            )
            .scalar()
        )
        exp = (
            db.session.query(func.coalesce(func.sum(Transaction.amount), Decimal('0.00')))
            .join(Category)
            .filter(
                Transaction.user_id == current_user.id,
                Category.type == 'expense',
                Transaction.transaction_date >= first_d,
                Transaction.transaction_date <= last_d
            )
            .scalar()
        )
        six_month_income.append(float(inc))
        six_month_expense.append(float(exp))

    has_6m_data = any(val > 0 for val in six_month_income) or any(val > 0 for val in six_month_expense)

    # 7. Current Month Budget Summary
    user_budgets = Budget.query.filter_by(
        user_id=current_user.id,
        month=today.month,
        year=today.year
    ).all()
    has_budgets = len(user_budgets) > 0
    total_budgeted = sum((b.amount for b in user_budgets), Decimal('0.00'))

    if has_budgets:
        budget_cat_ids = [b.category_id for b in user_budgets]
        budgeted_spent = (
            db.session.query(func.coalesce(func.sum(Transaction.amount), Decimal('0.00')))
            .join(Category)
            .filter(
                Transaction.user_id == current_user.id,
                Transaction.category_id.in_(budget_cat_ids),
                Category.type == 'expense',
                Transaction.transaction_date >= start_of_month,
                Transaction.transaction_date <= end_of_month
            )
            .scalar()
        )
        total_budget_spent = Decimal(str(budgeted_spent))
    else:
        total_budget_spent = Decimal('0.00')

    budget_percent = float((total_budget_spent / total_budgeted) * Decimal('100')) if total_budgeted > 0 else 0.0

    return render_template(
        'dashboard/index.html',
        current_month_name=current_month_name,
        monthly_income=monthly_income,
        monthly_expenses=monthly_expenses,
        net_balance=net_balance,
        monthly_tx_count=monthly_tx_count,
        recent_transactions=recent_transactions,
        category_labels=category_labels,
        category_amounts=category_amounts,
        has_expenses=has_expenses,
        monthly_labels=monthly_labels,
        six_month_income=six_month_income,
        six_month_expense=six_month_expense,
        has_6m_data=has_6m_data,
        has_budgets=has_budgets,
        total_budgeted=total_budgeted,
        total_budget_spent=total_budget_spent,
        budget_percent=round(budget_percent, 1)
    )
