"""WTForms form definitions for Transaction management."""

from datetime import date
from decimal import Decimal
from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, SelectField, TextAreaField, DateField, SubmitField
from wtforms.validators import InputRequired, DataRequired, Length, NumberRange, ValidationError, Optional
from app.extensions import db
from app.models import Category

PAYMENT_METHODS = [
    ('Cash', 'Cash'),
    ('Debit Card', 'Debit Card'),
    ('Credit Card', 'Credit Card'),
    ('Bank Transfer', 'Bank Transfer'),
    ('UPI / Digital Wallet', 'UPI / Digital Wallet'),
    ('Other', 'Other'),
]


def strip_filter(value):
    """Strip leading and trailing whitespace."""
    return value.strip() if isinstance(value, str) else value


class TransactionForm(FlaskForm):
    """Form for creating and editing financial transactions."""

    title = StringField(
        'Transaction Title',
        filters=[strip_filter],
        validators=[
            DataRequired(message="Title is required."),
            Length(min=1, max=100, message="Title must be between 1 and 100 characters.")
        ]
    )
    transaction_type = SelectField(
        'Transaction Type',
        choices=[('expense', 'Expense'), ('income', 'Income')],
        default='expense',
        validators=[DataRequired(message="Transaction type is required.")]
    )
    category_id = SelectField(
        'Category',
        coerce=int,
        validators=[DataRequired(message="Category is required.")]
    )
    amount = DecimalField(
        'Amount (₹)',
        places=2,
        validators=[
            InputRequired(message="Amount is required."),
            NumberRange(min=Decimal('0.01'), message="Amount must be greater than 0.00.")
        ]
    )
    payment_method = SelectField(
        'Payment Method',
        choices=PAYMENT_METHODS,
        validators=[DataRequired(message="Payment method is required.")]
    )
    description = TextAreaField(
        'Description (Optional)',
        filters=[strip_filter],
        validators=[
            Optional(),
            Length(max=255, message="Description must not exceed 255 characters.")
        ]
    )
    transaction_date = DateField(
        'Transaction Date',
        default=date.today,
        validators=[DataRequired(message="Transaction date is required.")]
    )
    submit = SubmitField('Save Transaction')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate all available categories dynamically
        categories = Category.query.order_by(Category.type.asc(), Category.name.asc()).all()
        self.category_id.choices = [(c.id, f"{c.name} ({c.type.capitalize()})") for c in categories]

    def validate_category_id(self, field):
        """Validate category existence and enforce matching category type."""
        category = db.session.get(Category, field.data)
        if not category:
            raise ValidationError("Selected category does not exist.")
        if category.type != self.transaction_type.data:
            raise ValidationError(
                f"Selected category '{category.name}' ({category.type}) does not match "
                f"the selected transaction type '{self.transaction_type.data}'."
            )
