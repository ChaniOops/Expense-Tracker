"""End-to-end user journey integration audit test suite."""

import csv
import io
import unittest
from datetime import date
from decimal import Decimal
from app import create_app
from app.extensions import db
from app.models import User, Category, Transaction, Budget, seed_categories


class TestEndToEndUserJourney(unittest.TestCase):
    """Complete 10-step user journey audit."""

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

        self.today = date.today()
        self.cat_salary = Category.query.filter_by(name='Salary', type='income').first()
        self.cat_food = Category.query.filter_by(name='Food', type='expense').first()
        self.cat_transport = Category.query.filter_by(name='Transport', type='expense').first()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_complete_user_lifecycle(self):
        """Execute complete user journey: Register -> Login -> Transactions -> Dashboard -> Budgets -> Reports -> CSV -> Logout."""
        # Step 1: Register a new account
        reg_resp = self.client.post('/register', data={
            'name': 'Aarav Gupta',
            'email': 'aarav@example.com',
            'password': 'SecurePassword123',
            'confirm_password': 'SecurePassword123'
        }, follow_redirects=True)
        self.assertEqual(reg_resp.status_code, 200)
        self.assertIn('Your account has been created successfully! Please sign in.', reg_resp.data.decode('utf-8'))

        user = User.query.filter_by(email='aarav@example.com').first()
        self.assertIsNotNone(user)
        self.assertTrue(user.check_password('SecurePassword123'))

        # Step 2: Log in
        login_resp = self.client.post('/login', data={
            'email': 'aarav@example.com',
            'password': 'SecurePassword123'
        }, follow_redirects=True)
        self.assertEqual(login_resp.status_code, 200)
        self.assertIn('Logged in as <strong>Aarav Gupta</strong>', login_resp.data.decode('utf-8'))

        # Step 3: Create income and expense transactions
        tx1_resp = self.client.post('/transactions/new', data={
            'title': 'Tech Corp Salary',
            'amount': '60000.00',
            'category_id': self.cat_salary.id,
            'transaction_type': 'income',
            'payment_method': 'Bank Transfer',
            'transaction_date': self.today.strftime('%Y-%m-%d'),
            'description': 'October monthly salary'
        }, follow_redirects=True)
        self.assertEqual(tx1_resp.status_code, 200)
        self.assertIn('Transaction created successfully!', tx1_resp.data.decode('utf-8'))

        tx2_resp = self.client.post('/transactions/new', data={
            'title': 'Supermarket Groceries',
            'amount': '2500.00',
            'category_id': self.cat_food.id,
            'transaction_type': 'expense',
            'payment_method': 'Credit Card',
            'transaction_date': self.today.strftime('%Y-%m-%d'),
            'description': 'Weekly food supplies'
        }, follow_redirects=True)
        self.assertEqual(tx2_resp.status_code, 200)
        self.assertIn('Transaction created successfully!', tx2_resp.data.decode('utf-8'))

        # Step 4: Edit and Delete transactions
        food_tx = Transaction.query.filter_by(title='Supermarket Groceries').first()
        self.assertIsNotNone(food_tx)
        edit_resp = self.client.post(f'/transactions/{food_tx.id}/edit', data={
            'title': 'Supermarket Groceries Updated',
            'amount': '3000.00',
            'category_id': self.cat_food.id,
            'transaction_type': 'expense',
            'payment_method': 'UPI / Digital Wallet',
            'transaction_date': self.today.strftime('%Y-%m-%d'),
            'description': 'Updated weekly food supplies'
        }, follow_redirects=True)
        self.assertEqual(edit_resp.status_code, 200)
        self.assertIn('Transaction updated successfully!', edit_resp.data.decode('utf-8'))

        # Add temporary transaction and delete it
        temp_tx = Transaction(
            user_id=user.id,
            category_id=self.cat_transport.id,
            title='Temporary Cab',
            amount=Decimal('500.00'),
            payment_method='Cash',
            transaction_date=self.today
        )
        db.session.add(temp_tx)
        db.session.commit()

        del_resp = self.client.post(f'/transactions/{temp_tx.id}/delete', follow_redirects=True)
        self.assertEqual(del_resp.status_code, 200)
        self.assertIn('Transaction deleted successfully.', del_resp.data.decode('utf-8'))
        self.assertIsNone(db.session.get(Transaction, temp_tx.id))

        # Add persistent transport expense
        tx3 = Transaction(
            user_id=user.id,
            category_id=self.cat_transport.id,
            title='Metro SmartCard',
            amount=Decimal('1500.00'),
            payment_method='Cash',
            transaction_date=self.today
        )
        db.session.add(tx3)
        db.session.commit()

        # Step 5: Search, filter, and sort transactions
        search_resp = self.client.get('/transactions?q=Groceries')
        search_html = search_resp.data.decode('utf-8')
        self.assertIn('Supermarket Groceries Updated', search_html)
        self.assertNotIn('Metro SmartCard', search_html)

        filter_resp = self.client.get(f'/transactions?type=expense&category_id={self.cat_food.id}')
        filter_html = filter_resp.data.decode('utf-8')
        self.assertIn('Supermarket Groceries Updated', filter_html)
        self.assertNotIn('Tech Corp Salary', filter_html)

        # Step 6: Inspect dashboard cards and charts
        dash_resp = self.client.get('/')
        self.assertEqual(dash_resp.status_code, 200)
        dash_html = dash_resp.data.decode('utf-8')
        self.assertIn('₹60,000.00', dash_html)  # Total Income
        self.assertIn('₹4,500.00', dash_html)   # Total Expense (3000 + 1500)
        self.assertIn('+₹55,500.00', dash_html) # Net Balance
        self.assertIn('data-has-expenses="true"', dash_html)

        # Step 7: Create and edit a monthly budget
        b_create_resp = self.client.post('/budgets/new', data={
            'category_id': self.cat_food.id,
            'amount': '5000.00',
            'month': self.today.month,
            'year': self.today.year
        }, follow_redirects=True)
        self.assertEqual(b_create_resp.status_code, 200)
        self.assertIn('Monthly budget created successfully!', b_create_resp.data.decode('utf-8'))

        food_budget = Budget.query.filter_by(user_id=user.id, category_id=self.cat_food.id).first()
        self.assertIsNotNone(food_budget)

        # Step 8: Verify budget thresholds:
        # Currently: Spent ₹3,000 / ₹5,000 = 60% (Normal)
        b_list_resp = self.client.get(f'/budgets?month={self.today.month}&year={self.today.year}')
        b_list_html = b_list_resp.data.decode('utf-8')
        self.assertIn('Normal', b_list_html)
        self.assertIn('60.0%', b_list_html)

        # Trigger Warning threshold (80% - 100%): add ₹1,200 Food expense -> total ₹4,200 (84%)
        warn_tx = Transaction(
            user_id=user.id,
            category_id=self.cat_food.id,
            title='Mid-Month Party Snacks',
            amount=Decimal('1200.00'),
            payment_method='UPI / Digital Wallet',
            transaction_date=self.today
        )
        db.session.add(warn_tx)
        db.session.commit()

        b_warn_resp = self.client.get(f'/budgets?month={self.today.month}&year={self.today.year}')
        b_warn_html = b_warn_resp.data.decode('utf-8')
        self.assertIn('⚠️ Approaching Limit', b_warn_html)
        self.assertIn('84.0%', b_warn_html)

        # Trigger Exceeded threshold (> 100%): add ₹1,000 Food expense -> total ₹5,200 (104%)
        exceed_tx = Transaction(
            user_id=user.id,
            category_id=self.cat_food.id,
            title='Luxury Dinner',
            amount=Decimal('1000.00'),
            payment_method='Credit Card',
            transaction_date=self.today
        )
        db.session.add(exceed_tx)
        db.session.commit()

        b_exceed_resp = self.client.get(f'/budgets?month={self.today.month}&year={self.today.year}')
        b_exceed_html = b_exceed_resp.data.decode('utf-8')
        self.assertIn('🚨 Budget Exceeded!', b_exceed_html)
        self.assertIn('104.0%', b_exceed_html)
        self.assertIn('₹200.00', b_exceed_html)  # Overspent amount: 5200 - 5000

        # Step 9: Generate monthly report
        rep_resp = self.client.get(f'/reports?month={self.today.month}&year={self.today.year}')
        self.assertEqual(rep_resp.status_code, 200)
        rep_html = rep_resp.data.decode('utf-8')
        # Total Income ₹60,000.00, Expenses: 3000 + 1500 + 1200 + 1000 = ₹6,700.00
        self.assertIn('₹60,000.00', rep_html)
        self.assertIn('₹6,700.00', rep_html)
        self.assertIn('+₹53,300.00', rep_html)
        # Largest expense is Supermarket Groceries Updated (₹3,000.00)
        self.assertIn('Supermarket Groceries Updated', rep_html)
        self.assertIn('₹3,000.00', rep_html)

        # Step 10: Export CSV
        csv_resp = self.client.get(f'/reports/export?month={self.today.month}&year={self.today.year}')
        self.assertEqual(csv_resp.status_code, 200)
        self.assertEqual(csv_resp.mimetype, 'text/csv')
        self.assertIn(f'attachment; filename="expense_tracker_report_{self.today.year}_{self.today.month:02d}.csv"', csv_resp.headers.get('Content-Disposition', ''))

        csv_reader = csv.reader(io.StringIO(csv_resp.data.decode('utf-8')))
        header = next(csv_reader)
        self.assertEqual(header, ['Date', 'Title', 'Category', 'Type', 'Amount', 'Payment Method', 'Description'])
        rows = list(csv_reader)
        self.assertEqual(len(rows), 5)  # 1 income + 4 expenses

        # Final Step: Log out and verify redirection
        logout_resp = self.client.post('/logout', follow_redirects=True)
        self.assertEqual(logout_resp.status_code, 200)
        self.assertIn('You have been logged out.', logout_resp.data.decode('utf-8'))

        # Protected view now redirects
        prot_resp = self.client.get('/')
        self.assertEqual(prot_resp.status_code, 302)
        self.assertIn('/login', prot_resp.headers['Location'])


if __name__ == '__main__':
    unittest.main()
