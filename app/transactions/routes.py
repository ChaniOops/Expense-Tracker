"""Transaction Blueprint routes for listing, creating, editing, and deleting transactions."""

from datetime import datetime, timezone
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Transaction, Category
from app.transactions import transactions_bp
from app.transactions.forms import TransactionForm

# Strict allowlist for ordering clauses to prevent arbitrary SQL injection
SORT_OPTIONS = {
    'date_desc': (Transaction.transaction_date.desc(), Transaction.id.desc()),
    'date_asc': (Transaction.transaction_date.asc(), Transaction.id.asc()),
    'amount_desc': (Transaction.amount.desc(), Transaction.id.desc()),
    'amount_asc': (Transaction.amount.asc(), Transaction.id.asc()),
}


@transactions_bp.route('/transactions', methods=['GET'])
@login_required
def index():
    """List, search, filter, and sort transactions scoped to current user."""
    # Retrieve query parameters
    search_query = request.args.get('q', '').strip()
    category_id_param = request.args.get('category_id', '').strip()
    tx_type_param = request.args.get('type', '').strip().lower()
    start_date_param = request.args.get('start_date', '').strip()
    end_date_param = request.args.get('end_date', '').strip()
    sort_by_param = request.args.get('sort_by', 'date_desc').strip()

    # Base query strictly isolated to current authenticated user
    query = Transaction.query.filter_by(user_id=current_user.id)

    # Search filter on title
    if search_query:
        query = query.filter(Transaction.title.ilike(f'%{search_query}%'))

    # Category filter
    selected_category_id = None
    if category_id_param:
        try:
            selected_category_id = int(category_id_param)
            query = query.filter(Transaction.category_id == selected_category_id)
        except ValueError:
            pass

    # Transaction type filter (joins Category to derive type)
    if tx_type_param in ('income', 'expense'):
        query = query.join(Category).filter(Category.type == tx_type_param)

    # Date range filters
    if start_date_param:
        try:
            parsed_start = datetime.strptime(start_date_param, '%Y-%m-%d').date()
            query = query.filter(Transaction.transaction_date >= parsed_start)
        except ValueError:
            pass

    if end_date_param:
        try:
            parsed_end = datetime.strptime(end_date_param, '%Y-%m-%d').date()
            query = query.filter(Transaction.transaction_date <= parsed_end)
        except ValueError:
            pass

    # Sort ordering with fallback to date_desc
    order_clause = SORT_OPTIONS.get(sort_by_param, SORT_OPTIONS['date_desc'])
    query = query.order_by(*order_clause)

    transactions = query.all()

    # Total unfiltered count for the current user
    total_user_transactions = Transaction.query.filter_by(user_id=current_user.id).count()

    # Determine if any filter or search is active
    is_filtered = bool(
        search_query
        or category_id_param
        or (tx_type_param in ('income', 'expense'))
        or start_date_param
        or end_date_param
        or (sort_by_param and sort_by_param != 'date_desc')
    )

    # Categories for filter dropdown
    all_categories = Category.query.order_by(Category.type.asc(), Category.name.asc()).all()

    return render_template(
        'transactions/list.html',
        transactions=transactions,
        total_user_transactions=total_user_transactions,
        is_filtered=is_filtered,
        categories=all_categories,
        search_query=search_query,
        selected_category_id=selected_category_id,
        selected_type=tx_type_param,
        start_date=start_date_param,
        end_date=end_date_param,
        sort_by=sort_by_param
    )


@transactions_bp.route('/transactions/new', methods=['GET', 'POST'])
@login_required
def create():
    """Create a new income or expense transaction."""
    form = TransactionForm()

    if form.validate_on_submit():
        transaction = Transaction(
            user_id=current_user.id,
            category_id=form.category_id.data,
            title=form.title.data,
            amount=form.amount.data,
            payment_method=form.payment_method.data,
            description=form.description.data,
            transaction_date=form.transaction_date.data
        )

        try:
            db.session.add(transaction)
            db.session.commit()
            flash("Transaction created successfully!", "success")
            return redirect(url_for('transactions.index'))
        except Exception:
            db.session.rollback()
            flash("An error occurred while saving the transaction. Please try again.", "danger")

    # Pass all categories with their type for dynamic UI filtering
    categories = Category.query.order_by(Category.name.asc()).all()
    categories_data = [{'id': c.id, 'name': c.name, 'type': c.type} for c in categories]

    return render_template(
        'transactions/form.html',
        form=form,
        action_title="Add New Transaction",
        categories_json=categories_data
    )


@transactions_bp.route('/transactions/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    """Edit an existing transaction owned by current user."""
    # Scope strictly by user_id to prevent IDOR
    transaction = Transaction.query.filter_by(id=id, user_id=current_user.id).first_or_404()

    form = TransactionForm(obj=transaction)

    # On initial GET, align the form's transaction_type with the category's actual type
    if request.method == 'GET' and transaction.category:
        form.transaction_type.data = transaction.category.type

    if form.validate_on_submit():
        transaction.title = form.title.data
        transaction.category_id = form.category_id.data
        transaction.amount = form.amount.data
        transaction.payment_method = form.payment_method.data
        transaction.description = form.description.data
        transaction.transaction_date = form.transaction_date.data
        transaction.updated_at = datetime.now(timezone.utc)

        try:
            db.session.commit()
            flash("Transaction updated successfully!", "success")
            return redirect(url_for('transactions.index'))
        except Exception:
            db.session.rollback()
            flash("An error occurred while updating the transaction. Please try again.", "danger")

    categories = Category.query.order_by(Category.name.asc()).all()
    categories_data = [{'id': c.id, 'name': c.name, 'type': c.type} for c in categories]

    return render_template(
        'transactions/form.html',
        form=form,
        action_title="Edit Transaction",
        transaction=transaction,
        categories_json=categories_data
    )


@transactions_bp.route('/transactions/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    """Delete a transaction owned by current user via CSRF-protected POST."""
    transaction = Transaction.query.filter_by(id=id, user_id=current_user.id).first_or_404()

    try:
        db.session.delete(transaction)
        db.session.commit()
        flash("Transaction deleted successfully.", "success")
    except Exception:
        db.session.rollback()
        flash("An error occurred while deleting the transaction. Please try again.", "danger")

    return redirect(url_for('transactions.index'))
