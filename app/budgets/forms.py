"""WTForms form definitions for monthly budget management."""

from datetime import date
from decimal import Decimal
from flask_login import current_user
from flask_wtf import FlaskForm
from wtforms import DecimalField, SelectField, IntegerField, SubmitField
from wtforms.validators import DataRequired, InputRequired, NumberRange, ValidationError
from app.extensions import db
from app.models import Category, Budget

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


class BudgetForm(FlaskForm):
    """Form for creating and editing monthly category budgets."""

    category_id = SelectField(
        'Expense Category',
        coerce=int,
        validators=[DataRequired(message="Please select an expense category.")]
    )
    amount = DecimalField(
        'Budget Amount (₹)',
        places=2,
        validators=[
            InputRequired(message="Budget amount is required."),
            NumberRange(min=Decimal('0.01'), message="Budget amount must be greater than 0.00.")
        ]
    )
    month = SelectField(
        'Month',
        coerce=int,
        choices=MONTH_CHOICES,
        default=lambda: date.today().month,
        validators=[DataRequired(message="Month is required.")]
    )
    year = IntegerField(
        'Year',
        default=lambda: date.today().year,
        validators=[
            DataRequired(message="Year is required."),
            NumberRange(min=2000, max=2100, message="Please enter a valid year between 2000 and 2100.")
        ]
    )
    submit = SubmitField('Save Budget')

    def __init__(self, *args, budget_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.budget_id = budget_id
        # Populate selector only with expense categories
        expense_categories = Category.query.filter_by(type='expense').order_by(Category.name.asc()).all()
        self.category_id.choices = [(c.id, c.name) for c in expense_categories]

    def validate_category_id(self, field):
        """Validate category existence and enforce that it is strictly an expense category."""
        category = db.session.get(Category, field.data)
        if not category:
            raise ValidationError("Selected category does not exist.")
        if category.type != 'expense':
            raise ValidationError("Budgets can only be assigned to expense categories.")

    def validate(self, extra_validators=None):
        """Cross-field validation enforcing unique (user, category, month, year)."""
        initial_validation = super().validate(extra_validators=extra_validators)
        if not initial_validation:
            return False

        # Enforce unique budget per (user_id, category_id, month, year)
        query = Budget.query.filter_by(
            user_id=current_user.id,
            category_id=self.category_id.data,
            month=self.month.data,
            year=self.year.data
        )
        if self.budget_id:
            query = query.filter(Budget.id != self.budget_id)

        if query.first():
            self.category_id.errors.append("A budget for this category, month, and year already exists.")
            return False

        return True
