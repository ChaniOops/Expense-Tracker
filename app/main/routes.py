"""Main Blueprint route controllers for Dashboard analytics and KPIs."""

import calendar
from datetime import date
from decimal import Decimal
from flask import render_template, request
from flask_login import login_required, current_user
from sqlalchemy import func
from app.extensions import db
from app.models import Transaction, Category, Budget
from app.main import main_bp

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
    period = request.args.get('period', 'month').lower().strip()
    if period not in ('month', 'year', 'all'):
        period = 'month'

    month_param = request.args.get('month')
    year_param = request.args.get('year')
    bar_view_param = request.args.get('bar_view', '6m')

    try:
        selected_month = int(month_param) if month_param else today.month
        if not (1 <= selected_month <= 12):
            selected_month = today.month
    except (ValueError, TypeError):
        selected_month = today.month

    try:
        selected_year = int(year_param) if year_param else today.year
        if not (2000 <= selected_year <= 2100):
            selected_year = today.year
    except (ValueError, TypeError):
        selected_year = today.year

    if bar_view_param not in ('month', '6m', 'year'):
        bar_view_param = '6m'

    start_of_month = date(selected_year, selected_month, 1)
    last_day_num = calendar.monthrange(selected_year, selected_month)[1]
    end_of_month = date(selected_year, selected_month, last_day_num)
    current_month_name = start_of_month.strftime('%B %Y')
    is_current_month = (selected_month == today.month and selected_year == today.year)

    available_years = list(range(today.year - 2, today.year + 3))
    if selected_year not in available_years:
        available_years.append(selected_year)
        available_years.sort()

    # Determine date boundaries based on selected period
    if period == 'all':
        overview_title = "All Time"
        period_label = "All time"
        tx_count_label = "All time logged"

        income_query = (
            db.session.query(func.coalesce(func.sum(Transaction.amount), Decimal('0.00')))
            .join(Category)
            .filter(
                Transaction.user_id == current_user.id,
                Category.type == 'income'
            )
        )
        expense_query = (
            db.session.query(func.coalesce(func.sum(Transaction.amount), Decimal('0.00')))
            .join(Category)
            .filter(
                Transaction.user_id == current_user.id,
                Category.type == 'expense'
            )
        )
        tx_count_query = Transaction.query.filter(Transaction.user_id == current_user.id)
        cat_expense_query = (
            db.session.query(Category.name, func.sum(Transaction.amount))
            .join(Category)
            .filter(
                Transaction.user_id == current_user.id,
                Category.type == 'expense'
            )
            .group_by(Category.name)
            .order_by(func.sum(Transaction.amount).desc())
        )
    elif period == 'year':
        year_start = date(selected_year, 1, 1)
        year_end = date(selected_year, 12, 31)
        overview_title = f"{selected_year}"
        period_label = f"Year {selected_year}"
        tx_count_label = f"Logged in {selected_year}"

        income_query = (
            db.session.query(func.coalesce(func.sum(Transaction.amount), Decimal('0.00')))
            .join(Category)
            .filter(
                Transaction.user_id == current_user.id,
                Category.type == 'income',
                Transaction.transaction_date >= year_start,
                Transaction.transaction_date <= year_end
            )
        )
        expense_query = (
            db.session.query(func.coalesce(func.sum(Transaction.amount), Decimal('0.00')))
            .join(Category)
            .filter(
                Transaction.user_id == current_user.id,
                Category.type == 'expense',
                Transaction.transaction_date >= year_start,
                Transaction.transaction_date <= year_end
            )
        )
        tx_count_query = Transaction.query.filter(
            Transaction.user_id == current_user.id,
            Transaction.transaction_date >= year_start,
            Transaction.transaction_date <= year_end
        )
        cat_expense_query = (
            db.session.query(Category.name, func.sum(Transaction.amount))
            .join(Category)
            .filter(
                Transaction.user_id == current_user.id,
                Category.type == 'expense',
                Transaction.transaction_date >= year_start,
                Transaction.transaction_date <= year_end
            )
            .group_by(Category.name)
            .order_by(func.sum(Transaction.amount).desc())
        )
    else:  # 'month'
        overview_title = current_month_name
        period_label = "Current month" if is_current_month else current_month_name
        tx_count_label = "Logged this month" if is_current_month else f"Logged in {current_month_name}"

        income_query = (
            db.session.query(func.coalesce(func.sum(Transaction.amount), Decimal('0.00')))
            .join(Category)
            .filter(
                Transaction.user_id == current_user.id,
                Category.type == 'income',
                Transaction.transaction_date >= start_of_month,
                Transaction.transaction_date <= end_of_month
            )
        )
        expense_query = (
            db.session.query(func.coalesce(func.sum(Transaction.amount), Decimal('0.00')))
            .join(Category)
            .filter(
                Transaction.user_id == current_user.id,
                Category.type == 'expense',
                Transaction.transaction_date >= start_of_month,
                Transaction.transaction_date <= end_of_month
            )
        )
        tx_count_query = Transaction.query.filter(
            Transaction.user_id == current_user.id,
            Transaction.transaction_date >= start_of_month,
            Transaction.transaction_date <= end_of_month
        )
        cat_expense_query = (
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
        )

    # 1. Income Total
    income_sum = income_query.scalar()
    monthly_income = Decimal(str(income_sum))

    # 2. Expense Total
    expense_sum = expense_query.scalar()
    monthly_expenses = Decimal(str(expense_sum))

    # 3. Net Balance & Transaction Count
    net_balance = monthly_income - monthly_expenses
    monthly_tx_count = tx_count_query.count()

    # 4. Recent Transactions (Latest 5 records)
    recent_transactions = (
        Transaction.query.filter_by(user_id=current_user.id)
        .order_by(Transaction.transaction_date.desc(), Transaction.created_at.desc(), Transaction.id.desc())
        .limit(5)
        .all()
    )

    # 5. Expense Breakdown by Category
    category_expenses = cat_expense_query.all()
    category_labels = [row[0] for row in category_expenses]
    category_amounts = [float(row[1]) for row in category_expenses]
    has_expenses = bool(monthly_expenses > 0 and len(category_amounts) > 0)

    # 6. Six-Month Cash Flow Trend (Ending in Selected Month)
    six_months = get_last_6_months(start_of_month)
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

    # 6b. Single Selected Month Cash Flow
    single_month_labels = [start_of_month.strftime('%b %Y')]
    single_month_income = [float(monthly_income)]
    single_month_expense = [float(monthly_expenses)]
    has_single_month_data = bool(monthly_income > 0 or monthly_expenses > 0)

    # 6c. Full Selected Year Cash Flow (12 Calendar Months)
    year_labels = []
    year_income = []
    year_expense = []
    for m in range(1, 13):
        m_start = date(selected_year, m, 1)
        m_last = date(selected_year, m, calendar.monthrange(selected_year, m)[1])
        year_labels.append(m_start.strftime('%b'))

        inc = (
            db.session.query(func.coalesce(func.sum(Transaction.amount), Decimal('0.00')))
            .join(Category)
            .filter(
                Transaction.user_id == current_user.id,
                Category.type == 'income',
                Transaction.transaction_date >= m_start,
                Transaction.transaction_date <= m_last
            )
            .scalar()
        )
        exp = (
            db.session.query(func.coalesce(func.sum(Transaction.amount), Decimal('0.00')))
            .join(Category)
            .filter(
                Transaction.user_id == current_user.id,
                Category.type == 'expense',
                Transaction.transaction_date >= m_start,
                Transaction.transaction_date <= m_last
            )
            .scalar()
        )
        year_income.append(float(inc))
        year_expense.append(float(exp))

    has_year_data = any(val > 0 for val in year_income) or any(val > 0 for val in year_expense)

    # 7. Selected Month Budget Summary
    user_budgets = Budget.query.filter_by(
        user_id=current_user.id,
        month=selected_month,
        year=selected_year
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
        period=period,
        overview_title=overview_title,
        period_label=period_label,
        tx_count_label=tx_count_label,
        selected_month=selected_month,
        selected_year=selected_year,
        month_choices=MONTH_CHOICES,
        available_years=available_years,
        is_current_month=is_current_month,
        bar_view=bar_view_param,
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
        single_month_labels=single_month_labels,
        single_month_income=single_month_income,
        single_month_expense=single_month_expense,
        has_single_month_data=has_single_month_data,
        year_labels=year_labels,
        year_income=year_income,
        year_expense=year_expense,
        has_year_data=has_year_data,
        has_budgets=has_budgets,
        total_budgeted=total_budgeted,
        total_budget_spent=total_budget_spent,
        budget_percent=round(budget_percent, 1)
    )
