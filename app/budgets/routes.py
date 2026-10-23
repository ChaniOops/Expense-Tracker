"""Budget Blueprint route controllers for monthly budget CRUD and spending calculations."""

import calendar
from datetime import date
from decimal import Decimal
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.models import Budget, Category, Transaction
from app.budgets import budgets_bp
from app.budgets.forms import BudgetForm, MONTH_CHOICES


@budgets_bp.route('/budgets', methods=['GET'])
@login_required
def index():
    """Display budgets for the selected month and year with spending progress."""
    today = date.today()

    # Parse and safely validate selected month and year
    try:
        selected_month = int(request.args.get('month', today.month))
        if selected_month < 1 or selected_month > 12:
            selected_month = today.month
    except (ValueError, TypeError):
        selected_month = today.month

    try:
        selected_year = int(request.args.get('year', today.year))
        if selected_year < 2000 or selected_year > 2100:
            selected_year = today.year
    except (ValueError, TypeError):
        selected_year = today.year

    # Calendar dates for the selected period
    start_date = date(selected_year, selected_month, 1)
    last_day_num = calendar.monthrange(selected_year, selected_month)[1]
    end_date = date(selected_year, selected_month, last_day_num)
    month_name = calendar.month_name[selected_month]

    # Query all budgets for current user for this period
    budgets = (
        Budget.query.filter_by(
            user_id=current_user.id,
            month=selected_month,
            year=selected_year
        )
        .join(Category)
        .order_by(Category.name.asc())
        .all()
    )

    budget_items = []
    total_budgeted = Decimal('0.00')
    total_spent = Decimal('0.00')

    for b in budgets:
        # Sum actual expenses for this user, category, and date range
        spent_sum = (
            db.session.query(func.coalesce(func.sum(Transaction.amount), Decimal('0.00')))
            .join(Category)
            .filter(
                Transaction.user_id == current_user.id,
                Transaction.category_id == b.category_id,
                Category.type == 'expense',
                Transaction.transaction_date >= start_date,
                Transaction.transaction_date <= end_date
            )
            .scalar()
        )
        actual_spent = Decimal(str(spent_sum))
        limit = b.amount

        # Percentage calculation (limit is guaranteed > 0.00)
        percentage = (actual_spent / limit) * Decimal('100')
        percentage_float = float(percentage)
        bar_percentage = min(percentage_float, 100.0)

        # Three-tier visual status determination
        if actual_spent > limit:
            status = 'exceeded'
            status_badge = '🚨 Budget Exceeded!'
            badge_class = 'bg-danger text-white'
            progress_bar_class = 'bg-danger'
            overspent = actual_spent - limit
            remaining = Decimal('0.00')
        elif percentage >= 80:
            status = 'warning'
            status_badge = '⚠️ Approaching Limit'
            badge_class = 'bg-warning text-dark'
            progress_bar_class = 'bg-warning text-dark'
            overspent = Decimal('0.00')
            remaining = limit - actual_spent
        else:
            status = 'normal'
            status_badge = 'Normal'
            badge_class = 'bg-success text-white'
            progress_bar_class = 'bg-success'
            overspent = Decimal('0.00')
            remaining = limit - actual_spent

        budget_items.append({
            'budget': b,
            'limit': limit,
            'spent': actual_spent,
            'remaining': remaining,
            'overspent': overspent,
            'is_exceeded': actual_spent > limit,
            'percentage': round(percentage_float, 1),
            'bar_percentage': round(bar_percentage, 1),
            'status': status,
            'status_badge': status_badge,
            'badge_class': badge_class,
            'progress_bar_class': progress_bar_class,
        })

        total_budgeted += limit
        total_spent += actual_spent

    total_remaining = max(Decimal('0.00'), total_budgeted - total_spent)
    total_overspent = max(Decimal('0.00'), total_spent - total_budgeted)

    # Years available for period selection dropdown
    available_years = list(range(today.year - 2, today.year + 3))

    return render_template(
        'budgets/index.html',
        budget_items=budget_items,
        selected_month=selected_month,
        selected_year=selected_year,
        month_name=month_name,
        month_choices=MONTH_CHOICES,
        available_years=available_years,
        total_budgeted=total_budgeted,
        total_spent=total_spent,
        total_remaining=total_remaining,
        total_overspent=total_overspent
    )


@budgets_bp.route('/budgets/new', methods=['GET', 'POST'])
@login_required
def create():
    """Create a new monthly expense budget."""
    form = BudgetForm()

    # Prepopulate month and year from query parameters if present on GET
    if request.method == 'GET':
        if 'month' in request.args:
            try:
                form.month.data = int(request.args.get('month'))
            except (ValueError, TypeError):
                pass
        if 'year' in request.args:
            try:
                form.year.data = int(request.args.get('year'))
            except (ValueError, TypeError):
                pass

    if form.validate_on_submit():
        budget = Budget(
            user_id=current_user.id,
            category_id=form.category_id.data,
            amount=form.amount.data,
            month=form.month.data,
            year=form.year.data
        )

        try:
            db.session.add(budget)
            db.session.commit()
            flash("Monthly budget created successfully!", "success")
            return redirect(url_for('budgets.index', month=budget.month, year=budget.year))
        except IntegrityError:
            db.session.rollback()
            flash("A budget for this category, month, and year already exists.", "danger")
        except Exception:
            db.session.rollback()
            flash("An error occurred while creating the budget. Please try again.", "danger")

    return render_template(
        'budgets/form.html',
        form=form,
        action_title="Set Monthly Budget",
        selected_month=form.month.data,
        selected_year=form.year.data
    )


@budgets_bp.route('/budgets/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    """Edit an existing budget owned by current user."""
    budget = Budget.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    form = BudgetForm(obj=budget, budget_id=budget.id)

    if form.validate_on_submit():
        budget.category_id = form.category_id.data
        budget.amount = form.amount.data
        budget.month = form.month.data
        budget.year = form.year.data

        try:
            db.session.commit()
            flash("Monthly budget updated successfully!", "success")
            return redirect(url_for('budgets.index', month=budget.month, year=budget.year))
        except IntegrityError:
            db.session.rollback()
            flash("A budget for this category, month, and year already exists.", "danger")
        except Exception:
            db.session.rollback()
            flash("An error occurred while updating the budget. Please try again.", "danger")

    return render_template(
        'budgets/form.html',
        form=form,
        action_title="Edit Monthly Budget",
        budget=budget,
        selected_month=budget.month,
        selected_year=budget.year
    )


@budgets_bp.route('/budgets/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    """Delete a budget owned by current user via CSRF-protected POST."""
    budget = Budget.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    target_month = budget.month
    target_year = budget.year

    try:
        db.session.delete(budget)
        db.session.commit()
        flash("Budget deleted successfully.", "success")
    except Exception:
        db.session.rollback()
        flash("An error occurred while deleting the budget.", "danger")

    return redirect(url_for('budgets.index', month=target_month, year=target_year))
