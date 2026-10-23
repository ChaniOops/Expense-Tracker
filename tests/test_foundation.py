"""Foundation and schema unit tests for Expense Tracker."""

import unittest
from datetime import date
from decimal import Decimal
from sqlalchemy.exc import IntegrityError
from app import create_app
from app.extensions import db
from app.models import User, Category, Transaction, Budget, seed_categories


class BaseTestCase(unittest.TestCase):
    """Base test case setting up an in-memory SQLite database."""

    def setUp(self):
        self.app = create_app({
            'TESTING': True,
            'WTF_CSRF_ENABLED': False,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        })
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()


class TestAppFoundation(BaseTestCase):
    """Verify application creation, blueprints, and basic routing."""

    def test_app_creation(self):
        """Test application initializes with testing configuration."""
        self.assertTrue(self.app.config['TESTING'])
        self.assertFalse(self.app.config['WTF_CSRF_ENABLED'])

    def test_blueprints_registered(self):
        """Verify all five required blueprints are registered."""
        blueprint_names = set(self.app.blueprints.keys())
        expected_blueprints = {'auth', 'main', 'transactions', 'budgets', 'reports'}
        self.assertTrue(expected_blueprints.issubset(blueprint_names))

    def test_index_route(self):
        """Test the root index route redirects to login when unauthenticated and loads when authenticated."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.location)

        # Authenticate user and verify 200
        user = User(name='Foundation Tester', email='foundation@example.com')
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()

        self.client.post('/login', data={'email': 'foundation@example.com', 'password': 'password123'})
        auth_response = self.client.get('/')
        self.assertEqual(auth_response.status_code, 200)
        self.assertIn(b'ExpenseTracker', auth_response.data)


class TestDatabaseSchema(BaseTestCase):
    """Verify tables, columns, constraints, and relationships."""

    def test_table_names(self):
        """Verify exactly the four required application tables exist."""
        table_names = set(db.metadata.tables.keys())
        expected_tables = {'users', 'categories', 'transactions', 'budgets'}
        self.assertEqual(table_names, expected_tables)

    def test_user_password_hashing_and_uniqueness(self):
        """Test password hashing, verification, and unique email constraint."""
        user1 = User(name='Alice Smith', email='alice@example.com')
        user1.set_password('securepassword123')
        db.session.add(user1)
        db.session.commit()

        self.assertTrue(user1.check_password('securepassword123'))
        self.assertFalse(user1.check_password('wrongpassword'))
        self.assertNotEqual(user1.password_hash, 'securepassword123')

        # Duplicate email test
        user2 = User(name='Alice Duplicate', email='alice@example.com')
        user2.set_password('anotherpassword')
        db.session.add(user2)
        with self.assertRaises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def test_category_constraints(self):
        """Test unique constraint on (name, type) and shared categories."""
        cat_expense_food = Category(name='Food', type='expense')
        db.session.add(cat_expense_food)
        db.session.commit()

        # Duplicate name under same type must fail
        cat_expense_food_dup = Category(name='Food', type='expense')
        db.session.add(cat_expense_food_dup)
        with self.assertRaises(IntegrityError):
            db.session.commit()
        db.session.rollback()

        # Same name under different types must succeed (e.g. 'Other' expense vs 'Other' income)
        cat_other_expense = Category(name='Other', type='expense')
        cat_other_income = Category(name='Other', type='income')
        db.session.add_all([cat_other_expense, cat_other_income])
        db.session.commit()
        self.assertIsNotNone(cat_other_expense.id)
        self.assertIsNotNone(cat_other_income.id)

    def test_transaction_decimal_and_derived_type(self):
        """Verify decimal precision and derived transaction type."""
        user = User(name='Bob Jones', email='bob@example.com')
        user.set_password('bobpassword')
        category = Category(name='Salary', type='income')
        db.session.add_all([user, category])
        db.session.commit()

        amount = Decimal('1250.75')
        tx = Transaction(
            user_id=user.id,
            category_id=category.id,
            title='Monthly Paycheck',
            amount=amount,
            payment_method='Bank Transfer',
            transaction_date=date(2026, 10, 1)
        )
        db.session.add(tx)
        db.session.commit()

        retrieved_tx = db.session.get(Transaction, tx.id)
        self.assertEqual(retrieved_tx.amount, amount)
        self.assertIsInstance(retrieved_tx.amount, Decimal)
        self.assertEqual(retrieved_tx.transaction_type, 'income')

    def test_budget_uniqueness_constraint(self):
        """Verify unique constraint on (user_id, category_id, month, year)."""
        user = User(name='Charlie Brown', email='charlie@example.com')
        user.set_password('charliepass')
        category = Category(name='Transport', type='expense')
        db.session.add_all([user, category])
        db.session.commit()

        budget1 = Budget(
            user_id=user.id,
            category_id=category.id,
            amount=Decimal('150.00'),
            month=10,
            year=2026
        )
        db.session.add(budget1)
        db.session.commit()

        # Duplicate budget for same category and month/year must raise IntegrityError
        budget2 = Budget(
            user_id=user.id,
            category_id=category.id,
            amount=Decimal('200.00'),
            month=10,
            year=2026
        )
        db.session.add(budget2)
        with self.assertRaises(IntegrityError):
            db.session.commit()
        db.session.rollback()


class TestCategorySeeding(BaseTestCase):
    """Verify idempotent category seeding."""

    def test_seeding_counts_and_idempotence(self):
        """Test default categories are created with expected counts and without duplicates."""
        seed_categories(db.session)

        all_categories = Category.query.all()
        self.assertEqual(len(all_categories), 15)

        expense_categories = Category.query.filter_by(type='expense').all()
        income_categories = Category.query.filter_by(type='income').all()
        self.assertEqual(len(expense_categories), 9)
        self.assertEqual(len(income_categories), 6)

        # Check 'Other' exists under both types
        other_cats = Category.query.filter_by(name='Other').all()
        self.assertEqual(len(other_cats), 2)
        types = {c.type for c in other_cats}
        self.assertEqual(types, {'income', 'expense'})

        # Re-run seeding to verify idempotence
        seed_categories(db.session)
        self.assertEqual(Category.query.count(), 15)


class TestForeignKeysAndCascades(BaseTestCase):
    """Verify foreign key enforcement and cascade rules."""

    def test_foreign_key_enforcement(self):
        """Verify invalid foreign keys raise IntegrityError."""
        # Non-existent user_id and category_id
        tx = Transaction(
            user_id=9999,
            category_id=9999,
            title='Ghost Transaction',
            amount=Decimal('10.00'),
            payment_method='Cash',
            transaction_date=date(2026, 10, 1)
        )
        db.session.add(tx)
        with self.assertRaises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def test_user_cascade_deletion(self):
        """Deleting a user cascades and deletes transactions and budgets."""
        user = User(name='David Miller', email='david@example.com')
        user.set_password('davidpass')
        category = Category(name='Shopping', type='expense')
        db.session.add_all([user, category])
        db.session.commit()

        tx = Transaction(
            user_id=user.id,
            category_id=category.id,
            title='Groceries',
            amount=Decimal('50.00'),
            payment_method='Debit Card',
            transaction_date=date(2026, 10, 1)
        )
        budget = Budget(
            user_id=user.id,
            category_id=category.id,
            amount=Decimal('200.00'),
            month=10,
            year=2026
        )
        db.session.add_all([tx, budget])
        db.session.commit()

        self.assertEqual(Transaction.query.filter_by(user_id=user.id).count(), 1)
        self.assertEqual(Budget.query.filter_by(user_id=user.id).count(), 1)

        # Delete user
        db.session.delete(user)
        db.session.commit()

        self.assertEqual(Transaction.query.filter_by(user_id=user.id).count(), 0)
        self.assertEqual(Budget.query.filter_by(user_id=user.id).count(), 0)

    def test_category_restrict_deletion(self):
        """Deleting a referenced category raises IntegrityError."""
        user = User(name='Eve Adams', email='eve@example.com')
        user.set_password('evepass')
        category = Category(name='Bills', type='expense')
        db.session.add_all([user, category])
        db.session.commit()

        tx = Transaction(
            user_id=user.id,
            category_id=category.id,
            title='Electricity',
            amount=Decimal('80.00'),
            payment_method='Debit Card',
            transaction_date=date(2026, 10, 1)
        )
        db.session.add(tx)
        db.session.commit()

        # Attempt to delete referenced category
        db.session.delete(category)
        with self.assertRaises(IntegrityError):
            db.session.commit()
        db.session.rollback()


if __name__ == '__main__':
    unittest.main()
