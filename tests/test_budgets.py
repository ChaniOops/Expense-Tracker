"""Automated unit test suite for monthly budget management, spending aggregation, alerts, and user isolation."""

import unittest
from datetime import date
from decimal import Decimal
from app import create_app
from app.extensions import db
from app.models import User, Category, Transaction, Budget, seed_categories


class BudgetTestCase(unittest.TestCase):
    """Base setup for budget testing."""

    def setUp(self):
        self.app = create_app({
            'TESTING': True,
            'WTF_CSRF_ENABLED': False,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'SERVER_NAME': 'localhost',
        })
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        db.create_all()
        seed_categories(db.session)

        # Create two test users for isolation tests
        self.user1 = User(name='Rohan Verma', email='rohan@example.com')
        self.user1.set_password('password123')
        self.user2 = User(name='Priya Sharma', email='priya@example.com')
        self.user2.set_password('password123')
        db.session.add_all([self.user1, self.user2])
        db.session.commit()

        # Cache reference categories
        self.cat_food = Category.query.filter_by(name='Food', type='expense').first()
        self.cat_transport = Category.query.filter_by(name='Transport', type='expense').first()
        self.cat_utilities = Category.query.filter_by(name='Utilities', type='expense').first()
        self.cat_salary = Category.query.filter_by(name='Salary', type='income').first()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def login_as(self, email='rohan@example.com', password='password123'):
        return self.client.post('/login', data={'email': email, 'password': password}, follow_redirects=True)


class TestBudgetCRUD(BudgetTestCase):
    """Test creation, viewing, editing, deletion, and validation of monthly budgets."""

    def test_create_valid_budget(self):
        """User can create an expense budget with valid amount, month, and year."""
        self.login_as('rohan@example.com')
        response = self.client.post('/budgets/new', data={
            'category_id': self.cat_food.id,
            'amount': '5000.00',
            'month': 10,
            'year': 2026
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('Monthly budget created successfully!', response.data.decode('utf-8'))

        budget = Budget.query.filter_by(
            user_id=self.user1.id,
            category_id=self.cat_food.id,
            month=10,
            year=2026
        ).first()
        self.assertIsNotNone(budget)
        self.assertEqual(budget.amount, Decimal('5000.00'))

    def test_edit_budget(self):
        """User can update their budget amount, month, or year."""
        budget = Budget(
            user_id=self.user1.id,
            category_id=self.cat_food.id,
            amount=Decimal('5000.00'),
            month=10,
            year=2026
        )
        db.session.add(budget)
        db.session.commit()

        self.login_as('rohan@example.com')
        response = self.client.post(f'/budgets/{budget.id}/edit', data={
            'category_id': self.cat_food.id,
            'amount': '7500.00',
            'month': 10,
            'year': 2026
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('Monthly budget updated successfully!', response.data.decode('utf-8'))

        db.session.refresh(budget)
        self.assertEqual(budget.amount, Decimal('7500.00'))

    def test_delete_budget_post(self):
        """User can delete a budget via POST."""
        budget = Budget(
            user_id=self.user1.id,
            category_id=self.cat_transport.id,
            amount=Decimal('3000.00'),
            month=10,
            year=2026
        )
        db.session.add(budget)
        db.session.commit()
        b_id = budget.id

        self.login_as('rohan@example.com')
        response = self.client.post(f'/budgets/{b_id}/delete', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Budget deleted successfully.', response.data.decode('utf-8'))

        self.assertIsNone(db.session.get(Budget, b_id))

    def test_reject_delete_budget_via_get(self):
        """GET request to budget delete route must be rejected with 405 Method Not Allowed."""
        budget = Budget(
            user_id=self.user1.id,
            category_id=self.cat_transport.id,
            amount=Decimal('3000.00'),
            month=10,
            year=2026
        )
        db.session.add(budget)
        db.session.commit()

        self.login_as('rohan@example.com')
        response = self.client.get(f'/budgets/{budget.id}/delete')
        self.assertEqual(response.status_code, 405)

    def test_reject_zero_and_negative_amounts(self):
        """Zero and negative budget amounts must be rejected by server validation."""
        self.login_as('rohan@example.com')

        # Test zero amount
        res_zero = self.client.post('/budgets/new', data={
            'category_id': self.cat_food.id,
            'amount': '0.00',
            'month': 10,
            'year': 2026
        })
        self.assertEqual(res_zero.status_code, 200)
        self.assertIn('Budget amount must be greater than 0.00.', res_zero.data.decode('utf-8'))

        # Test negative amount
        res_neg = self.client.post('/budgets/new', data={
            'category_id': self.cat_food.id,
            'amount': '-500.00',
            'month': 10,
            'year': 2026
        })
        self.assertEqual(res_neg.status_code, 200)
        self.assertIn('Budget amount must be greater than 0.00.', res_neg.data.decode('utf-8'))

        # Verify no record created
        self.assertEqual(Budget.query.count(), 0)

    def test_reject_income_category_for_budget(self):
        """Budgets cannot be assigned to income categories."""
        self.login_as('rohan@example.com')
        response = self.client.post('/budgets/new', data={
            'category_id': self.cat_salary.id,
            'amount': '50000.00',
            'month': 10,
            'year': 2026
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('Budgets can only be assigned to expense categories.', response.data.decode('utf-8'))
        self.assertEqual(Budget.query.count(), 0)

    def test_reject_duplicate_budget_same_user_category_period(self):
        """Reject duplicate budget for the same user, category, month, and year."""
        budget = Budget(
            user_id=self.user1.id,
            category_id=self.cat_food.id,
            amount=Decimal('5000.00'),
            month=10,
            year=2026
        )
        db.session.add(budget)
        db.session.commit()

        self.login_as('rohan@example.com')
        response = self.client.post('/budgets/new', data={
            'category_id': self.cat_food.id,
            'amount': '6000.00',
            'month': 10,
            'year': 2026
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('A budget for this category, month, and year already exists.', response.data.decode('utf-8'))
        self.assertEqual(Budget.query.filter_by(user_id=self.user1.id).count(), 1)

    def test_allow_same_category_and_period_for_different_users(self):
        """Different users can each have a budget for the same category, month, and year."""
        budget1 = Budget(
            user_id=self.user1.id,
            category_id=self.cat_food.id,
            amount=Decimal('5000.00'),
            month=10,
            year=2026
        )
        db.session.add(budget1)
        db.session.commit()

        self.login_as('priya@example.com')
        response = self.client.post('/budgets/new', data={
            'category_id': self.cat_food.id,
            'amount': '8000.00',
            'month': 10,
            'year': 2026
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        # Both budgets should exist
        self.assertEqual(Budget.query.filter_by(category_id=self.cat_food.id, month=10, year=2026).count(), 2)


class TestBudgetSpendingAndAlerts(BudgetTestCase):
    """Test spending calculations, threshold alerts, dynamic consistency, and boundary exclusions."""

    def test_spending_calculation_and_exclusions(self):
        """Calculate spending matching user, category, and period, excluding income, other categories, other months, and other users."""
        # Setup budget for User 1: Food, Oct 2026, limit ₹10,000
        budget = Budget(
            user_id=self.user1.id,
            category_id=self.cat_food.id,
            amount=Decimal('10000.00'),
            month=10,
            year=2026
        )
        db.session.add(budget)

        # 1. Matching expense transaction (₹3,000)
        tx_match = Transaction(
            user_id=self.user1.id,
            category_id=self.cat_food.id,
            amount=Decimal('3000.00'),
            title='Groceries',
            transaction_date=date(2026, 10, 15),
            payment_method='Cash'
        )
        # 2. Expense transaction in different month (Nov 2026, ₹2,000) -> EXCLUDED
        tx_diff_month = Transaction(
            user_id=self.user1.id,
            category_id=self.cat_food.id,
            amount=Decimal('2000.00'),
            title='Nov Groceries',
            transaction_date=date(2026, 11, 5),
            payment_method='Cash'
        )
        # 3. Expense transaction in different category (Transport, Oct 2026, ₹1,500) -> EXCLUDED
        tx_diff_cat = Transaction(
            user_id=self.user1.id,
            category_id=self.cat_transport.id,
            amount=Decimal('1500.00'),
            title='Bus Pass',
            transaction_date=date(2026, 10, 10),
            payment_method='Cash'
        )
        # 4. Income transaction in Oct 2026 (Salary, ₹50,000) -> EXCLUDED
        tx_income = Transaction(
            user_id=self.user1.id,
            category_id=self.cat_salary.id,
            amount=Decimal('50000.00'),
            title='Monthly Salary',
            transaction_date=date(2026, 10, 1),
            payment_method='Bank Transfer'
        )
        # 5. Expense transaction for User 2 (Food, Oct 2026, ₹4,000) -> EXCLUDED
        tx_user2 = Transaction(
            user_id=self.user2.id,
            category_id=self.cat_food.id,
            amount=Decimal('4000.00'),
            title='User 2 Food',
            transaction_date=date(2026, 10, 20),
            payment_method='UPI'
        )
        db.session.add_all([tx_match, tx_diff_month, tx_diff_cat, tx_income, tx_user2])
        db.session.commit()

        self.login_as('rohan@example.com')
        response = self.client.get('/budgets?month=10&year=2026')
        self.assertEqual(response.status_code, 200)

        html = response.data.decode('utf-8')
        # Total budgeted ₹10,000.00
        self.assertIn('₹10,000.00', html)
        # Actual spent ₹3,000.00
        self.assertIn('₹3,000.00', html)
        # Remaining ₹7,000.00
        self.assertIn('₹7,000.00', html)
        # Percentage: 30.0%
        self.assertIn('30.0%', html)
        # Status badge: Normal
        self.assertIn('Normal', html)

    def test_warning_threshold_at_80_percent(self):
        """Spending at or exceeding 80% but <= 100% shows warning state."""
        budget = Budget(
            user_id=self.user1.id,
            category_id=self.cat_food.id,
            amount=Decimal('1000.00'),
            month=10,
            year=2026
        )
        # Spend exactly 80% (₹800.00)
        tx = Transaction(
            user_id=self.user1.id,
            category_id=self.cat_food.id,
            amount=Decimal('800.00'),
            title='Dinner',
            transaction_date=date(2026, 10, 12),
            payment_method='Card'
        )
        db.session.add_all([budget, tx])
        db.session.commit()

        self.login_as('rohan@example.com')
        response = self.client.get('/budgets?month=10&year=2026')
        self.assertEqual(response.status_code, 200)

        html = response.data.decode('utf-8')
        self.assertIn('⚠️ Approaching Limit', html)
        self.assertIn('80.0%', html)
        self.assertIn('₹200.00', html)  # Remaining
        self.assertIn('bg-warning', html)

    def test_exceeded_budget_state(self):
        """Spending exceeding 100% triggers exceeded status, overspent amount, and danger styling."""
        budget = Budget(
            user_id=self.user1.id,
            category_id=self.cat_food.id,
            amount=Decimal('1000.00'),
            month=10,
            year=2026
        )
        # Spend 120% (₹1,200.00)
        tx = Transaction(
            user_id=self.user1.id,
            category_id=self.cat_food.id,
            amount=Decimal('1200.00'),
            title='Fine Dining',
            transaction_date=date(2026, 10, 18),
            payment_method='Card'
        )
        db.session.add_all([budget, tx])
        db.session.commit()

        self.login_as('rohan@example.com')
        response = self.client.get('/budgets?month=10&year=2026')
        self.assertEqual(response.status_code, 200)

        html = response.data.decode('utf-8')
        self.assertIn('🚨 Budget Exceeded!', html)
        self.assertIn('120.0%', html)
        self.assertIn('Overspent:', html)
        self.assertIn('₹200.00', html)  # Overspent amount: 1200 - 1000
        self.assertIn('bg-danger', html)

    def test_spending_reflects_transaction_lifecycle(self):
        """Budget spending dynamically recalculates when transactions are added, edited, or deleted."""
        budget = Budget(
            user_id=self.user1.id,
            category_id=self.cat_transport.id,
            amount=Decimal('2000.00'),
            month=10,
            year=2026
        )
        db.session.add(budget)
        db.session.commit()

        self.login_as('rohan@example.com')

        # 1. Initially zero spending
        res1 = self.client.get('/budgets?month=10&year=2026')
        html1 = res1.data.decode('utf-8')
        self.assertIn('₹0.00', html1)
        self.assertIn('0.0%', html1)

        # 2. Add an expense transaction
        tx = Transaction(
            user_id=self.user1.id,
            category_id=self.cat_transport.id,
            amount=Decimal('500.00'),
            title='Fuel',
            transaction_date=date(2026, 10, 5),
            payment_method='UPI'
        )
        db.session.add(tx)
        db.session.commit()

        res2 = self.client.get('/budgets?month=10&year=2026')
        html2 = res2.data.decode('utf-8')
        self.assertIn('₹500.00', html2)
        self.assertIn('25.0%', html2)

        # 3. Edit transaction amount to ₹1,800.00 (90% - warning threshold)
        tx.amount = Decimal('1800.00')
        db.session.commit()

        res3 = self.client.get('/budgets?month=10&year=2026')
        html3 = res3.data.decode('utf-8')
        self.assertIn('₹1,800.00', html3)
        self.assertIn('90.0%', html3)
        self.assertIn('⚠️ Approaching Limit', html3)

        # 4. Delete the transaction
        db.session.delete(tx)
        db.session.commit()

        res4 = self.client.get('/budgets?month=10&year=2026')
        html4 = res4.data.decode('utf-8')
        self.assertIn('₹0.00', html4)
        self.assertIn('0.0%', html4)
        self.assertIn('Normal', html4)

    def test_december_to_january_boundary_filtering(self):
        """Calendar filtering strictly respects December vs January boundaries."""
        budget_dec = Budget(
            user_id=self.user1.id,
            category_id=self.cat_food.id,
            amount=Decimal('5000.00'),
            month=12,
            year=2026
        )
        budget_jan = Budget(
            user_id=self.user1.id,
            category_id=self.cat_food.id,
            amount=Decimal('5000.00'),
            month=1,
            year=2027
        )
        tx_dec31 = Transaction(
            user_id=self.user1.id,
            category_id=self.cat_food.id,
            amount=Decimal('1500.00'),
            title='New Year Eve Groceries',
            transaction_date=date(2026, 12, 31),
            payment_method='Cash'
        )
        tx_jan01 = Transaction(
            user_id=self.user1.id,
            category_id=self.cat_food.id,
            amount=Decimal('2200.00'),
            title='New Year Day Lunch',
            transaction_date=date(2027, 1, 1),
            payment_method='Cash'
        )
        db.session.add_all([budget_dec, budget_jan, tx_dec31, tx_jan01])
        db.session.commit()

        self.login_as('rohan@example.com')

        # Check December 2026
        res_dec = self.client.get('/budgets?month=12&year=2026')
        html_dec = res_dec.data.decode('utf-8')
        self.assertIn('December 2026', html_dec)
        self.assertIn('₹1,500.00', html_dec)
        self.assertNotIn('₹2,200.00', html_dec)

        # Check January 2027
        res_jan = self.client.get('/budgets?month=1&year=2027')
        html_jan = res_jan.data.decode('utf-8')
        self.assertIn('January 2027', html_jan)
        self.assertIn('₹2,200.00', html_jan)
        self.assertNotIn('₹1,500.00', html_jan)


class TestBudgetSecurityAndIsolation(BudgetTestCase):
    """Test authentication guards, IDOR prevention, and CSRF protection."""

    def test_unauthenticated_access_redirects(self):
        """Unauthenticated requests to budget routes redirect to login."""
        endpoints = [
            ('/budgets', 'GET'),
            ('/budgets/new', 'GET'),
            ('/budgets/new', 'POST'),
            ('/budgets/1/edit', 'GET'),
            ('/budgets/1/edit', 'POST'),
            ('/budgets/1/delete', 'POST'),
        ]
        for url, method in endpoints:
            if method == 'GET':
                resp = self.client.get(url)
            else:
                resp = self.client.post(url)
            self.assertEqual(resp.status_code, 302, f"Failed for {method} {url}")
            self.assertIn('/login', resp.headers['Location'])

    def test_multi_tenant_idor_protection(self):
        """User Two cannot view, edit, or delete User One's budget."""
        budget_user1 = Budget(
            user_id=self.user1.id,
            category_id=self.cat_food.id,
            amount=Decimal('5000.00'),
            month=10,
            year=2026
        )
        db.session.add(budget_user1)
        db.session.commit()
        b_id = budget_user1.id

        # Log in as User 2 (Priya)
        self.login_as('priya@example.com')

        # User 2 list should show empty state for this period
        resp_list = self.client.get('/budgets?month=10&year=2026')
        self.assertEqual(resp_list.status_code, 200)
        self.assertIn('No Monthly Budgets Defined', resp_list.data.decode('utf-8'))

        # Attempt to edit User 1's budget -> 404
        resp_edit_get = self.client.get(f'/budgets/{b_id}/edit')
        self.assertEqual(resp_edit_get.status_code, 404)

        resp_edit_post = self.client.post(f'/budgets/{b_id}/edit', data={
            'category_id': self.cat_food.id,
            'amount': '9999.00',
            'month': 10,
            'year': 2026
        })
        self.assertEqual(resp_edit_post.status_code, 404)

        # Attempt to delete User 1's budget -> 404
        resp_delete = self.client.post(f'/budgets/{b_id}/delete')
        self.assertEqual(resp_delete.status_code, 404)

        # Verify User 1's budget was untouched
        db.session.refresh(budget_user1)
        self.assertEqual(budget_user1.amount, Decimal('5000.00'))

    def test_csrf_protection_enabled(self):
        """With CSRF enabled, POST without valid CSRF token is rejected."""
        csrf_app = create_app({
            'TESTING': True,
            'WTF_CSRF_ENABLED': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'SERVER_NAME': 'localhost',
        })
        with csrf_app.app_context():
            db.create_all()
            seed_categories(db.session)
            u = User(name='CSRF User', email='csrf@example.com')
            u.set_password('password123')
            db.session.add(u)
            db.session.commit()

            c = csrf_app.test_client()
            c.post('/login', data={'email': 'csrf@example.com', 'password': 'password123'})

            cat = Category.query.filter_by(type='expense').first()

            # Attempt POST without CSRF token
            resp = c.post('/budgets/new', data={
                'category_id': cat.id,
                'amount': '1000.00',
                'month': 10,
                'year': 2026
            })
            self.assertEqual(resp.status_code, 400)
            db.session.remove()
            db.drop_all()

    def test_inr_formatting_on_budgets_page(self):
        """Monetary values are rendered using ₹ and Indian numbering."""
        budget = Budget(
            user_id=self.user1.id,
            category_id=self.cat_food.id,
            amount=Decimal('125000.00'),
            month=10,
            year=2026
        )
        db.session.add(budget)
        db.session.commit()

        self.login_as('rohan@example.com')
        response = self.client.get('/budgets?month=10&year=2026')
        self.assertEqual(response.status_code, 200)

        html = response.data.decode('utf-8')
        # ₹1,25,000.00 with Indian formatting
        self.assertIn('₹1,25,000.00', html)


if __name__ == '__main__':
    unittest.main()
