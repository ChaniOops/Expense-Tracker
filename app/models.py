"""Database models and idempotent seeding logic."""

from datetime import datetime, timezone
from decimal import Decimal
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


class User(UserMixin, db.Model):
    """User account entity for authentication and data isolation."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    transactions = db.relationship('Transaction', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    budgets = db.relationship('Budget', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, password):
        """Hash and store the user's password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verify the password against the stored hash."""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User id={self.id} email='{self.email}'>"


class Category(db.Model):
    """Shared lookup category entity."""
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(10), nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    transactions = db.relationship('Transaction', backref='category', lazy='dynamic')
    budgets = db.relationship('Budget', backref='category', lazy='dynamic')

    __table_args__ = (
        db.UniqueConstraint('name', 'type', name='uq_categories_name_type'),
        db.CheckConstraint("type IN ('income', 'expense')", name='ck_categories_type'),
    )

    def __repr__(self):
        return f"<Category id={self.id} name='{self.name}' type='{self.type}'>"


class Transaction(db.Model):
    """User financial transaction entity."""
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id', ondelete='RESTRICT'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Numeric(10, 2, asdecimal=True), nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    transaction_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        db.CheckConstraint('amount > 0.00', name='ck_transactions_amount'),
        db.Index('ix_transactions_user_date', 'user_id', db.text('transaction_date DESC')),
        db.Index('ix_transactions_user_category', 'user_id', 'category_id'),
    )

    @property
    def transaction_type(self):
        """Derive transaction direction ('income' vs 'expense') from category."""
        return self.category.type if self.category else None

    def __repr__(self):
        return f"<Transaction id={self.id} title='{self.title}' amount={self.amount}>"


class Budget(db.Model):
    """Monthly spending limit entity for an expense category."""
    __tablename__ = 'budgets'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id', ondelete='RESTRICT'), nullable=False)
    amount = db.Column(db.Numeric(10, 2, asdecimal=True), nullable=False)
    month = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.UniqueConstraint('user_id', 'category_id', 'month', 'year', name='uq_budgets_user_cat_month_year'),
        db.CheckConstraint('amount > 0.00', name='ck_budgets_amount'),
        db.CheckConstraint('month >= 1 AND month <= 12', name='ck_budgets_month'),
        db.CheckConstraint('year >= 2000', name='ck_budgets_year'),
        db.Index('ix_budgets_user_period', 'user_id', 'year', 'month'),
    )

    def __repr__(self):
        return f"<Budget id={self.id} category_id={self.category_id} month={self.month} year={self.year} amount={self.amount}>"


# Default Category Specifications
DEFAULT_CATEGORIES = [
    # Expense categories
    ("Food", "expense"),
    ("Transport", "expense"),
    ("Shopping", "expense"),
    ("Entertainment", "expense"),
    ("Education", "expense"),
    ("Bills", "expense"),
    ("Healthcare", "expense"),
    ("Travel", "expense"),
    ("Other", "expense"),
    # Income categories
    ("Salary", "income"),
    ("Freelance", "income"),
    ("Scholarship", "income"),
    ("Allowance", "income"),
    ("Investment", "income"),
    ("Other", "income"),
]


def seed_categories(session=None):
    """Idempotently seed default expense and income categories."""
    target_session = session or db.session
    added = False
    for name, cat_type in DEFAULT_CATEGORIES:
        existing = target_session.query(Category).filter_by(name=name, type=cat_type).first()
        if not existing:
            target_session.add(Category(name=name, type=cat_type))
            added = True
    if added:
        target_session.commit()
