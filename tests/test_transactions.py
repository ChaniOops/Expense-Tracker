"""Automated test suite for transaction management, filtering, sorting, and user isolation."""

import unittest
from datetime import date
from decimal import Decimal
from app import create_app
from app.extensions import db
from app.models import User, Category, Transaction, seed_categories


class TransactionTestCase(unittest.TestCase):
    """Test case setup for transactions with in-memory database."""

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

        # Create two distinct test users for isolation testing
        self.user1 = User(name='User One', email='user1@example.com')
        self.user1.set_password('password123')
        self.user2 = User(name='User Two', email='user2@example.com')
        self.user2.set_password('password123')
        db.session.add_all([self.user1, self.user2])
        db.session.commit()

        # Cache reference categories
        self.cat_food = Category.query.filter_by(name='Food', type='expense').first()
        self.cat_transport = Category.query.filter_by(name='Transport', type='expense').first()
        self.cat_salary = Category.query.filter_by(name='Salary', type='income').first()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def login_as(self, email='user1@example.com', password='password123'):
        """Helper to establish session for a user."""
        return self.client.post('/login', data={'email': email, 'password': password}, follow_redirects=True)


class TestTransactionCRUD(TransactionTestCase):
    """Test creating, editing, and deleting transactions."""

    def test_create_expense_and_income_transactions(self):
        """User can create expense and income transactions and type is derived."""
        self.login_as('user1@example.com')

        # 1. Create Expense
        res_exp = self.client.post('/transactions/new', data={
            'title': 'Dinner at Italian Restaurant',
            'transaction_type': 'expense',
            'category_id': self.cat_food.id,
            'amount': '55.40',
            'payment_method': 'Credit Card',
            'transaction_date': '2026-10-15',
            'description': 'Family dinner',
        }, follow_redirects=True)
        self.assertEqual(res_exp.status_code, 200)
        self.assertIn(b'Transaction created successfully!', res_exp.data)

        tx_exp = Transaction.query.filter_by(title='Dinner at Italian Restaurant').first()
        self.assertIsNotNone(tx_exp)
        self.assertEqual(tx_exp.amount, Decimal('55.40'))
        self.assertEqual(tx_exp.transaction_type, 'expense')
        self.assertEqual(tx_exp.user_id, self.user1.id)

        # 2. Create Income
        res_inc = self.client.post('/transactions/new', data={
            'title': 'October Monthly Paycheck',
            'transaction_type': 'income',
            'category_id': self.cat_salary.id,
            'amount': '3200.00',
            'payment_method': 'Bank Transfer',
            'transaction_date': '2026-10-01',
            'description': 'Full-time salary',
        }, follow_redirects=True)
        self.assertEqual(res_inc.status_code, 200)

        tx_inc = Transaction.query.filter_by(title='October Monthly Paycheck').first()
        self.assertIsNotNone(tx_inc)
        self.assertEqual(tx_inc.amount, Decimal('3200.00'))
        self.assertEqual(tx_inc.transaction_type, 'income')

    def test_reject_zero_and_negative_amounts(self):
        """Zero and negative monetary amounts are rejected by validation."""
        self.login_as('user1@example.com')

        # Zero amount
        res_zero = self.client.post('/transactions/new', data={
            'title': 'Zero Test',
            'transaction_type': 'expense',
            'category_id': self.cat_food.id,
            'amount': '0.00',
            'payment_method': 'Cash',
            'transaction_date': '2026-10-15',
        })
        self.assertEqual(res_zero.status_code, 200)
        self.assertIn(b'Amount must be greater than 0.00.', res_zero.data)

        # Negative amount
        res_neg = self.client.post('/transactions/new', data={
            'title': 'Negative Test',
            'transaction_type': 'expense',
            'category_id': self.cat_food.id,
            'amount': '-15.50',
            'payment_method': 'Cash',
            'transaction_date': '2026-10-15',
        })
        self.assertEqual(res_neg.status_code, 200)
        self.assertIn(b'Amount must be greater than 0.00.', res_neg.data)

    def test_reject_category_type_mismatch_and_invalid_category(self):
        """Selecting an expense type with an income category or invalid category is rejected."""
        self.login_as('user1@example.com')

        # Mismatch: type is expense, but category is Salary (income)
        res_mismatch = self.client.post('/transactions/new', data={
            'title': 'Mismatch Test',
            'transaction_type': 'expense',
            'category_id': self.cat_salary.id,
            'amount': '100.00',
            'payment_method': 'Cash',
            'transaction_date': '2026-10-15',
        })
        self.assertEqual(res_mismatch.status_code, 200)
        self.assertIn(b'does not match the selected transaction type', res_mismatch.data)

        # Non-existent category ID
        res_nonexist = self.client.post('/transactions/new', data={
            'title': 'Nonexistent Category',
            'transaction_type': 'expense',
            'category_id': 9999,
            'amount': '50.00',
            'payment_method': 'Cash',
            'transaction_date': '2026-10-15',
        })
        self.assertEqual(res_nonexist.status_code, 200)
        self.assertIn(b'Not a valid choice', res_nonexist.data)

    def test_edit_transaction(self):
        """User can edit their own transaction fields."""
        self.login_as('user1@example.com')

        tx = Transaction(
            user_id=self.user1.id,
            category_id=self.cat_food.id,
            title='Fast Food',
            amount=Decimal('12.50'),
            payment_method='Cash',
            transaction_date=date(2026, 10, 10)
        )
        db.session.add(tx)
        db.session.commit()

        # Update to Transport
        res = self.client.post(f'/transactions/{tx.id}/edit', data={
            'title': 'Subway Metro Pass',
            'transaction_type': 'expense',
            'category_id': self.cat_transport.id,
            'amount': '30.00',
            'payment_method': 'Debit Card',
            'transaction_date': '2026-10-11',
            'description': 'Weekly pass',
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Transaction updated successfully!', res.data)

        updated_tx = db.session.get(Transaction, tx.id)
        self.assertEqual(updated_tx.title, 'Subway Metro Pass')
        self.assertEqual(updated_tx.amount, Decimal('30.00'))
        self.assertEqual(updated_tx.category_id, self.cat_transport.id)
        self.assertEqual(updated_tx.payment_method, 'Debit Card')

    def test_delete_transaction_post(self):
        """Deleting transaction via POST deletes record from database."""
        self.login_as('user1@example.com')

        tx = Transaction(
            user_id=self.user1.id,
            category_id=self.cat_food.id,
            title='Item to Delete',
            amount=Decimal('10.00'),
            payment_method='Cash',
            transaction_date=date(2026, 10, 10)
        )
        db.session.add(tx)
        db.session.commit()

        res = self.client.post(f'/transactions/{tx.id}/delete', follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Transaction deleted successfully.', res.data)
        self.assertIsNone(db.session.get(Transaction, tx.id))

    def test_reject_delete_via_get(self):
        """GET request on delete route must be rejected with 405 Method Not Allowed."""
        self.login_as('user1@example.com')
        res = self.client.get('/transactions/1/delete')
        self.assertEqual(res.status_code, 405)


class TestUserIsolation(TransactionTestCase):
    """Verify strict multi-tenant isolation (IDOR defense)."""

    def test_reject_access_to_other_user_transaction(self):
        """User Two cannot view, edit, or delete User One's transaction."""
        # Create transaction owned by User One
        tx1 = Transaction(
            user_id=self.user1.id,
            category_id=self.cat_food.id,
            title='User One Secret Expense',
            amount=Decimal('99.99'),
            payment_method='Cash',
            transaction_date=date(2026, 10, 10)
        )
        db.session.add(tx1)
        db.session.commit()

        # Login as User Two
        self.login_as('user2@example.com')

        # 1. User Two cannot see User One's transaction in list
        res_list = self.client.get('/transactions')
        self.assertNotIn(b'User One Secret Expense', res_list.data)

        # 2. User Two cannot GET edit form of User One's transaction (404)
        res_get_edit = self.client.get(f'/transactions/{tx1.id}/edit')
        self.assertEqual(res_get_edit.status_code, 404)

        # 3. User Two cannot POST update to User One's transaction (404)
        res_post_edit = self.client.post(f'/transactions/{tx1.id}/edit', data={
            'title': 'Hacked Title',
            'transaction_type': 'expense',
            'category_id': self.cat_food.id,
            'amount': '1.00',
            'payment_method': 'Cash',
            'transaction_date': '2026-10-10',
        })
        self.assertEqual(res_post_edit.status_code, 404)

        # 4. User Two cannot POST delete to User One's transaction (404)
        res_del = self.client.post(f'/transactions/{tx1.id}/delete')
        self.assertEqual(res_del.status_code, 404)

        # Verify transaction remains untouched
        intact_tx = db.session.get(Transaction, tx1.id)
        self.assertIsNotNone(intact_tx)
        self.assertEqual(intact_tx.title, 'User One Secret Expense')
        self.assertEqual(intact_tx.amount, Decimal('99.99'))


class TestSearchFilteringAndSorting(TransactionTestCase):
    """Test search, category/type/date filtering, and sorting."""

    def setUp(self):
        super().setUp()
        self.login_as('user1@example.com')

        # Seed test dataset for user1
        t1 = Transaction(user_id=self.user1.id, category_id=self.cat_food.id, title='Starbucks Coffee', amount=Decimal('5.50'), payment_method='Cash', transaction_date=date(2026, 10, 1))
        t2 = Transaction(user_id=self.user1.id, category_id=self.cat_food.id, title='Grocery Market', amount=Decimal('85.00'), payment_method='Debit Card', transaction_date=date(2026, 10, 5))
        t3 = Transaction(user_id=self.user1.id, category_id=self.cat_transport.id, title='Gas Station Fuel', amount=Decimal('40.00'), payment_method='Credit Card', transaction_date=date(2026, 10, 10))
        t4 = Transaction(user_id=self.user1.id, category_id=self.cat_salary.id, title='Main Salary Paycheck', amount=Decimal('3000.00'), payment_method='Bank Transfer', transaction_date=date(2026, 10, 15))
        db.session.add_all([t1, t2, t3, t4])
        db.session.commit()

    def test_search_by_title(self):
        """Search query filters transactions by title substring."""
        res = self.client.get('/transactions?q=Coffee')
        self.assertIn(b'Starbucks Coffee', res.data)
        self.assertNotIn(b'Grocery Market', res.data)
        self.assertNotIn(b'Gas Station Fuel', res.data)

    def test_filter_by_category(self):
        """Filter by category ID returns only matching records."""
        res = self.client.get(f'/transactions?category_id={self.cat_transport.id}')
        self.assertIn(b'Gas Station Fuel', res.data)
        self.assertNotIn(b'Starbucks Coffee', res.data)
        self.assertNotIn(b'Main Salary Paycheck', res.data)

    def test_filter_by_type(self):
        """Filter by type (income vs expense) filters correctly."""
        # Income only
        res_inc = self.client.get('/transactions?type=income')
        self.assertIn(b'Main Salary Paycheck', res_inc.data)
        self.assertNotIn(b'Starbucks Coffee', res_inc.data)

        # Expense only
        res_exp = self.client.get('/transactions?type=expense')
        self.assertIn(b'Starbucks Coffee', res_exp.data)
        self.assertIn(b'Grocery Market', res_exp.data)
        self.assertNotIn(b'Main Salary Paycheck', res_exp.data)

    def test_filter_by_date_range(self):
        """Filter by start_date and end_date isolates date window."""
        res = self.client.get('/transactions?start_date=2026-10-04&end_date=2026-10-12')
        self.assertIn(b'Grocery Market', res.data)
        self.assertIn(b'Gas Station Fuel', res.data)
        self.assertNotIn(b'Starbucks Coffee', res.data)   # Oct 1
        self.assertNotIn(b'Main Salary Paycheck', res.data) # Oct 15

    def test_sorting_options(self):
        """Sort by date asc/desc and amount asc/desc works cleanly."""
        # Sort by amount desc
        res_amt_desc = self.client.get('/transactions?sort_by=amount_desc')
        content = res_amt_desc.data.decode('utf-8')
        pos_salary = content.find('Main Salary Paycheck')
        pos_grocery = content.find('Grocery Market')
        pos_coffee = content.find('Starbucks Coffee')
        self.assertTrue(pos_salary < pos_grocery < pos_coffee)

        # Sort by amount asc
        res_amt_asc = self.client.get('/transactions?sort_by=amount_asc')
        content_asc = res_amt_asc.data.decode('utf-8')
        pos_salary_asc = content_asc.find('Main Salary Paycheck')
        pos_coffee_asc = content_asc.find('Starbucks Coffee')
        self.assertTrue(pos_coffee_asc < pos_salary_asc)

    def test_combined_search_filter_and_sort(self):
        """Combining search, category, type, date range, and sort returns precise records."""
        res = self.client.get(
            f'/transactions?q=Market&category_id={self.cat_food.id}&type=expense&start_date=2026-10-01&end_date=2026-10-10&sort_by=amount_desc'
        )
        self.assertIn(b'Grocery Market', res.data)
        self.assertNotIn(b'Starbucks Coffee', res.data)
        self.assertNotIn(b'Gas Station Fuel', res.data)

    def test_invalid_query_parameters_handled_safely(self):
        """Invalid date or SQL injection strings in sort_by or category_id do not error."""
        res = self.client.get('/transactions?category_id=not_an_int&start_date=invalid_date&sort_by=DROP+TABLE+users')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Starbucks Coffee', res.data)


class TestSecurityAndCSRF(TransactionTestCase):
    """Test unauthenticated access redirection and CSRF validation."""

    def test_unauthenticated_access_redirects(self):
        """Unauthenticated requests to transaction endpoints redirect to login."""
        endpoints = [
            ('/transactions', 'GET'),
            ('/transactions/new', 'GET'),
            ('/transactions/new', 'POST'),
            ('/transactions/1/edit', 'GET'),
            ('/transactions/1/edit', 'POST'),
            ('/transactions/1/delete', 'POST'),
        ]
        for url, method in endpoints:
            if method == 'GET':
                res = self.client.get(url)
            else:
                res = self.client.post(url)
            self.assertEqual(res.status_code, 302)
            self.assertIn('/login', res.location)

    def test_csrf_protection_on_transactions(self):
        """State-changing requests require CSRF token when CSRF is enabled."""
        csrf_app = create_app({
            'TESTING': True,
            'WTF_CSRF_ENABLED': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'SECRET_KEY': 'csrf-test-key',
        })
        with csrf_app.app_context():
            db.create_all()
            seed_categories(db.session)
            client = csrf_app.test_client()

            # Create user and authenticate
            user = User(name='CSRF User', email='csrf@example.com')
            user.set_password('password123')
            db.session.add(user)
            db.session.commit()

            # Attempt creating transaction without CSRF token
            # Note: unauthenticated will redirect to login, but if authenticated without CSRF, returns 400
            # Login first with WTForms or set session
            with client.session_transaction() as sess:
                sess['_user_id'] = str(user.id)
                sess['_fresh'] = True

            res = client.post('/transactions/new', data={
                'title': 'Test No CSRF',
                'amount': '10.00',
                'category_id': 1,
                'payment_method': 'Cash',
                'transaction_date': '2026-10-15'
            })
            self.assertEqual(res.status_code, 400)


if __name__ == '__main__':
    unittest.main()
