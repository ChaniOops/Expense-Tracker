"""Automated unit test suite for Dashboard KPIs, analytics, charts, and user isolation."""

import unittest
from datetime import date, timedelta
from decimal import Decimal
from app import create_app
from app.extensions import db
from app.models import User, Category, Transaction, seed_categories
from app.main.routes import get_last_6_months


class DashboardTestCase(unittest.TestCase):
    """Test case setup for dashboard testing."""

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

        # Create two test users
        self.user1 = User(name='Anil Sharma', email='anil@example.com')
        self.user1.set_password('password123')
        self.user2 = User(name='Sunita Patel', email='sunita@example.com')
        self.user2.set_password('password123')
        db.session.add_all([self.user1, self.user2])
        db.session.commit()

        # Cache reference categories
        self.cat_salary = Category.query.filter_by(name='Salary', type='income').first()
        self.cat_freelance = Category.query.filter_by(name='Freelance', type='income').first()
        self.cat_food = Category.query.filter_by(name='Food', type='expense').first()
        self.cat_transport = Category.query.filter_by(name='Transport', type='expense').first()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def login_as(self, email='anil@example.com', password='password123'):
        return self.client.post('/login', data={'email': email, 'password': password}, follow_redirects=True)


class TestDashboardCalculations(DashboardTestCase):
    """Test KPI calculations, month boundary exclusions, and INR display."""

    def test_empty_dashboard_for_new_user(self):
        """New user with no records sees zeroed metrics and clean empty states."""
        self.login_as('anil@example.com')
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

        html = response.data.decode('utf-8')
        self.assertIn('₹0.00', html)
        self.assertIn('No Transactions Found', html)
        self.assertIn('No Expenses Recorded', html)
        self.assertIn('No Activity In The Last 6 Months', html)

    def test_current_month_kpis_and_boundary_exclusion(self):
        """Dashboard accurately calculates current-month totals and excludes other months."""
        self.login_as('anil@example.com')
        today = date.today()

        # Current month transactions for user1
        tx1 = Transaction(user_id=self.user1.id, category_id=self.cat_salary.id, title='Monthly Pay', amount=Decimal('80000.00'), payment_method='Bank Transfer', transaction_date=today)
        tx2 = Transaction(user_id=self.user1.id, category_id=self.cat_food.id, title='Grocery Haul', amount=Decimal('12500.00'), payment_method='Debit Card', transaction_date=today)
        tx3 = Transaction(user_id=self.user1.id, category_id=self.cat_transport.id, title='Fuel', amount=Decimal('2500.00'), payment_method='Cash', transaction_date=today)

        # Previous month transaction (should be excluded from current month cards)
        # Safely compute a date in the previous calendar month
        first_of_this_month = date(today.year, today.month, 1)
        prev_month_date = first_of_this_month - timedelta(days=5)
        tx_prev = Transaction(user_id=self.user1.id, category_id=self.cat_salary.id, title='Old Pay', amount=Decimal('70000.00'), payment_method='Bank Transfer', transaction_date=prev_month_date)

        # Next month transaction (should be excluded from current month cards)
        if today.month == 12:
            next_month_date = date(today.year + 1, 1, 15)
        else:
            next_month_date = date(today.year, today.month + 1, 15)
        tx_next = Transaction(user_id=self.user1.id, category_id=self.cat_food.id, title='Future Dining', amount=Decimal('5000.00'), payment_method='Credit Card', transaction_date=next_month_date)

        db.session.add_all([tx1, tx2, tx3, tx_prev, tx_next])
        db.session.commit()

        response = self.client.get('/')
        html = response.data.decode('utf-8')

        # Current month Income: ₹80,000.00
        self.assertIn('₹80,000.00', html)
        # Current month Expense: ₹15,000.00 (12500 + 2500)
        self.assertIn('₹15,000.00', html)
        # Net balance: ₹65,000.00 (80000 - 15000)
        self.assertIn('+₹65,000.00', html)
        # Monthly transaction count: exactly 3 (tx1, tx2, tx3)
        self.assertIn('>3<', html)

        # Verify old pay and future dining are not in current month totals
        self.assertNotIn('₹1,50,000.00', html)
        self.assertNotIn('₹20,000.00', html)

    def test_negative_net_balance_styling(self):
        """Deficit net balance is shown with danger styling and minus sign."""
        self.login_as('anil@example.com')
        today = date.today()

        # Income 10,000, Expense 15,000 -> Net -₹5,000.00
        tx1 = Transaction(user_id=self.user1.id, category_id=self.cat_freelance.id, title='Gig', amount=Decimal('10000.00'), payment_method='UPI / Digital Wallet', transaction_date=today)
        tx2 = Transaction(user_id=self.user1.id, category_id=self.cat_food.id, title='Big Feast', amount=Decimal('15000.00'), payment_method='Credit Card', transaction_date=today)
        db.session.add_all([tx1, tx2])
        db.session.commit()

        response = self.client.get('/')
        html = response.data.decode('utf-8')
        self.assertIn('text-danger', html)
        self.assertIn('-₹5,000.00', html)


class TestDashboardRecentAndCharts(DashboardTestCase):
    """Test recent transactions table limit and Chart.js datasets."""

    def test_recent_transactions_limit_and_order(self):
        """Recent transactions table displays only the latest 5 transactions in descending order."""
        self.login_as('anil@example.com')
        today = date.today()

        created_txs = []
        for i in range(1, 8):
            tx_date = today - timedelta(days=i)
            tx = Transaction(
                user_id=self.user1.id,
                category_id=self.cat_food.id,
                title=f'Transaction Item {i}',
                amount=Decimal(f'{i * 100}.00'),
                payment_method='Cash',
                transaction_date=tx_date
            )
            created_txs.append(tx)
        db.session.add_all(created_txs)
        db.session.commit()

        response = self.client.get('/')
        html = response.data.decode('utf-8')

        # Items 1 to 5 (most recent dates) must appear
        for i in range(1, 6):
            self.assertIn(f'Transaction Item {i}', html)

        # Items 6 and 7 must be excluded by the 5-item limit
        self.assertNotIn('Transaction Item 6', html)
        self.assertNotIn('Transaction Item 7', html)

        # Chronological descending order check (Item 1 before Item 5)
        pos_item1 = html.find('Transaction Item 1')
        pos_item5 = html.find('Transaction Item 5')
        self.assertTrue(pos_item1 < pos_item5)

    def test_expense_breakdown_by_category_chart_data(self):
        """Current month category breakdown accurately groups expenses."""
        self.login_as('anil@example.com')
        today = date.today()

        t1 = Transaction(user_id=self.user1.id, category_id=self.cat_food.id, title='Groceries', amount=Decimal('2500.00'), payment_method='Cash', transaction_date=today)
        t2 = Transaction(user_id=self.user1.id, category_id=self.cat_food.id, title='Snacks', amount=Decimal('1500.00'), payment_method='Cash', transaction_date=today)
        t3 = Transaction(user_id=self.user1.id, category_id=self.cat_transport.id, title='Cab', amount=Decimal('1000.00'), payment_method='Debit Card', transaction_date=today)
        db.session.add_all([t1, t2, t3])
        db.session.commit()

        response = self.client.get('/')
        html = response.data.decode('utf-8')

        # Check chart data encoded attributes
        self.assertIn('data-has-expenses="true"', html)
        self.assertIn('Food', html)
        self.assertIn('Transport', html)
        # Food total: 2500 + 1500 = 4000.0
        self.assertIn('4000.0', html)
        # Transport total: 1000.0
        self.assertIn('1000.0', html)


class TestDateTransitionsAndIsolation(DashboardTestCase):
    """Test 6-month date calculation helper, year transitions, and user data isolation."""

    def test_december_to_january_year_transition(self):
        """get_last_6_months handles January date and rolls back across previous year correctly."""
        jan_date = date(2026, 1, 15)
        months = get_last_6_months(jan_date)
        self.assertEqual(len(months), 6)

        labels = [m[2] for m in months]
        expected_labels = ['Aug 2025', 'Sep 2025', 'Oct 2025', 'Nov 2025', 'Dec 2025', 'Jan 2026']
        self.assertEqual(labels, expected_labels)

        # Check date boundaries
        # Aug 2025
        self.assertEqual(months[0][0], date(2025, 8, 1))
        self.assertEqual(months[0][1], date(2025, 8, 31))
        # Dec 2025
        self.assertEqual(months[4][0], date(2025, 12, 1))
        self.assertEqual(months[4][1], date(2025, 12, 31))
        # Jan 2026
        self.assertEqual(months[5][0], date(2026, 1, 1))
        self.assertEqual(months[5][1], date(2026, 1, 31))

    def test_multi_tenant_dashboard_isolation(self):
        """User Two cannot see User One's financial statistics, transactions, or charts."""
        today = date.today()

        # Seed substantial transactions for User One
        tx1 = Transaction(user_id=self.user1.id, category_id=self.cat_salary.id, title='Secret Executive Pay', amount=Decimal('500000.00'), payment_method='Bank Transfer', transaction_date=today)
        tx2 = Transaction(user_id=self.user1.id, category_id=self.cat_food.id, title='Luxury Meal', amount=Decimal('80000.00'), payment_method='Credit Card', transaction_date=today)
        db.session.add_all([tx1, tx2])
        db.session.commit()

        # Login as User Two
        self.login_as('sunita@example.com')
        response = self.client.get('/')
        html = response.data.decode('utf-8')

        # User Two should see zero metrics and empty states
        self.assertIn('₹0.00', html)
        self.assertNotIn('₹5,00,000.00', html)
        self.assertNotIn('₹80,000.00', html)
        self.assertNotIn('Secret Executive Pay', html)
        self.assertNotIn('Luxury Meal', html)
        self.assertIn('No Transactions Found', html)

    def test_unauthenticated_dashboard_redirects(self):
        """Unauthenticated request to dashboard redirects to login."""
        res = self.client.get('/')
        self.assertEqual(res.status_code, 302)
        self.assertIn('/login', res.location)


if __name__ == '__main__':
    unittest.main()
