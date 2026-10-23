"""Automated unit test suite for monthly financial reports, CSV export, formula injection mitigation, and user isolation."""

import csv
import io
import unittest
from datetime import date
from decimal import Decimal
from app import create_app
from app.extensions import db
from app.models import User, Category, Transaction, seed_categories


class ReportsTestCase(unittest.TestCase):
    """Base test setup for monthly reports and CSV export."""

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

        # Create two test users for data isolation testing
        self.user1 = User(name='Karan Mehta', email='karan@example.com')
        self.user1.set_password('password123')
        self.user2 = User(name='Ananya Sen', email='ananya@example.com')
        self.user2.set_password('password123')
        db.session.add_all([self.user1, self.user2])
        db.session.commit()

        # Cache reference categories
        self.cat_salary = Category.query.filter_by(name='Salary', type='income').first()
        self.cat_freelance = Category.query.filter_by(name='Freelance', type='income').first()
        self.cat_food = Category.query.filter_by(name='Food', type='expense').first()
        self.cat_transport = Category.query.filter_by(name='Transport', type='expense').first()
        self.cat_entertainment = Category.query.filter_by(name='Entertainment', type='expense').first()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def login_as(self, email='karan@example.com', password='password123'):
        return self.client.post('/login', data={'email': email, 'password': password}, follow_redirects=True)


class TestReportCalculations(ReportsTestCase):
    """Test monthly summary calculations, boundary exclusions, breakdowns, and largest expense."""

    def test_monthly_summary_and_boundary_exclusion(self):
        """Report calculates correct totals and excludes transactions from other months and years."""
        # User 1 target month transactions (Oct 2026)
        tx_income = Transaction(
            user_id=self.user1.id,
            category_id=self.cat_salary.id,
            amount=Decimal('50000.00'),
            title='October Salary',
            transaction_date=date(2026, 10, 1),
            payment_method='Bank Transfer'
        )
        tx_exp1 = Transaction(
            user_id=self.user1.id,
            category_id=self.cat_food.id,
            amount=Decimal('8000.00'),
            title='Groceries',
            transaction_date=date(2026, 10, 10),
            payment_method='Card'
        )
        tx_exp2 = Transaction(
            user_id=self.user1.id,
            category_id=self.cat_transport.id,
            amount=Decimal('2000.00'),
            title='Fuel',
            transaction_date=date(2026, 10, 20),
            payment_method='UPI'
        )

        # Other months and years (Excluded)
        tx_sep = Transaction(
            user_id=self.user1.id,
            category_id=self.cat_salary.id,
            amount=Decimal('45000.00'),
            title='September Salary',
            transaction_date=date(2026, 9, 30),
            payment_method='Bank Transfer'
        )
        tx_nov = Transaction(
            user_id=self.user1.id,
            category_id=self.cat_food.id,
            amount=Decimal('7000.00'),
            title='November Groceries',
            transaction_date=date(2026, 11, 1),
            payment_method='Card'
        )
        tx_diff_year = Transaction(
            user_id=self.user1.id,
            category_id=self.cat_food.id,
            amount=Decimal('5000.00'),
            title='Last Year Groceries',
            transaction_date=date(2025, 10, 15),
            payment_method='Cash'
        )
        db.session.add_all([tx_income, tx_exp1, tx_exp2, tx_sep, tx_nov, tx_diff_year])
        db.session.commit()

        self.login_as('karan@example.com')
        response = self.client.get('/reports?month=10&year=2026')
        self.assertEqual(response.status_code, 200)

        html = response.data.decode('utf-8')
        # Total Income: ₹50,000.00
        self.assertIn('₹50,000.00', html)
        # Total Expenses: ₹10,000.00
        self.assertIn('₹10,000.00', html)
        # Net Balance: +₹40,000.00
        self.assertIn('+₹40,000.00', html)
        # Transaction Count: 3
        self.assertIn('3', html)
        # Excluded amounts should not appear
        self.assertNotIn('₹45,000.00', html)
        self.assertNotIn('₹7,000.00', html)

    def test_empty_report_month(self):
        """Month with zero transactions renders zeroed values and clean empty states."""
        self.login_as('karan@example.com')
        response = self.client.get('/reports?month=4&year=2026')
        self.assertEqual(response.status_code, 200)

        html = response.data.decode('utf-8')
        self.assertIn('₹0.00', html)
        self.assertIn('No expense transactions recorded in this period.', html)
        self.assertIn('No expense categories recorded for this month.', html)
        self.assertIn('No transactions found for April 2026.', html)

    def test_category_wise_expense_breakdown(self):
        """Category breakdown calculates category totals, percentages, and sorts descending."""
        tx1 = Transaction(
            user_id=self.user1.id,
            category_id=self.cat_food.id,
            amount=Decimal('6000.00'),
            title='Food Expense',
            transaction_date=date(2026, 10, 5),
            payment_method='Cash'
        )
        tx2 = Transaction(
            user_id=self.user1.id,
            category_id=self.cat_transport.id,
            amount=Decimal('4000.00'),
            title='Transport Expense',
            transaction_date=date(2026, 10, 8),
            payment_method='UPI'
        )
        tx3 = Transaction(
            user_id=self.user1.id,
            category_id=self.cat_salary.id,
            amount=Decimal('20000.00'),
            title='Income',
            transaction_date=date(2026, 10, 1),
            payment_method='Bank Transfer'
        )
        db.session.add_all([tx1, tx2, tx3])
        db.session.commit()

        self.login_as('karan@example.com')
        response = self.client.get('/reports?month=10&year=2026')
        self.assertEqual(response.status_code, 200)

        html = response.data.decode('utf-8')
        # Total expenses is 10,000. Food is 60%, Transport is 40%
        self.assertIn('₹6,000.00', html)
        self.assertIn('60.0%', html)
        self.assertIn('₹4,000.00', html)
        self.assertIn('40.0%', html)
        # Income category must not be in expense breakdown
        # Find breakdown section in HTML
        breakdown_idx = html.find('Category-Wise Expense Breakdown')
        ledger_idx = html.find('Period Transaction Ledger')
        breakdown_html = html[breakdown_idx:ledger_idx]
        self.assertNotIn('Salary', breakdown_html)

    def test_largest_expense_selection(self):
        """Identify the largest expense, ignoring larger income transactions and breaking ties deterministically."""
        # Large income (must be ignored)
        tx_income = Transaction(
            user_id=self.user1.id,
            category_id=self.cat_salary.id,
            amount=Decimal('80000.00'),
            title='Salary Big',
            transaction_date=date(2026, 10, 1),
            payment_method='Bank Transfer'
        )
        # Expense 1 (₹3,000)
        tx_exp1 = Transaction(
            user_id=self.user1.id,
            category_id=self.cat_food.id,
            amount=Decimal('3000.00'),
            title='Dining Out',
            transaction_date=date(2026, 10, 5),
            payment_method='Card'
        )
        # Expense 2 (₹12,000 - Largest)
        tx_exp2 = Transaction(
            user_id=self.user1.id,
            category_id=self.cat_entertainment.id,
            amount=Decimal('12000.00'),
            title='Concert Tickets',
            transaction_date=date(2026, 10, 15),
            payment_method='UPI'
        )
        db.session.add_all([tx_income, tx_exp1, tx_exp2])
        db.session.commit()

        self.login_as('karan@example.com')
        response = self.client.get('/reports?month=10&year=2026')
        self.assertEqual(response.status_code, 200)

        html = response.data.decode('utf-8')
        self.assertIn('Concert Tickets', html)
        self.assertIn('Entertainment', html)
        self.assertIn('₹12,000.00', html)

    def test_monthly_transaction_ledger_ordering(self):
        """Ledger displays transactions ordered by date descending."""
        tx_old = Transaction(
            user_id=self.user1.id,
            category_id=self.cat_food.id,
            amount=Decimal('100.00'),
            title='Earlier Event',
            transaction_date=date(2026, 10, 2),
            payment_method='Cash'
        )
        tx_new = Transaction(
            user_id=self.user1.id,
            category_id=self.cat_food.id,
            amount=Decimal('200.00'),
            title='Later Event',
            transaction_date=date(2026, 10, 25),
            payment_method='Cash'
        )
        db.session.add_all([tx_old, tx_new])
        db.session.commit()

        self.login_as('karan@example.com')
        response = self.client.get('/reports?month=10&year=2026')
        html = response.data.decode('utf-8')

        later_idx = html.find('Later Event')
        earlier_idx = html.find('Earlier Event')
        self.assertTrue(later_idx < earlier_idx, "Newer transaction must appear before older transaction.")

    def test_inr_formatting_on_report_page(self):
        """Amounts on report page are formatted with ₹ and Indian numeral groupings."""
        tx = Transaction(
            user_id=self.user1.id,
            category_id=self.cat_salary.id,
            amount=Decimal('1250000.00'),
            title='Annual Bonus',
            transaction_date=date(2026, 10, 10),
            payment_method='Bank Transfer'
        )
        db.session.add(tx)
        db.session.commit()

        self.login_as('karan@example.com')
        response = self.client.get('/reports?month=10&year=2026')
        self.assertEqual(response.status_code, 200)
        self.assertIn('₹12,50,000.00', response.data.decode('utf-8'))


class TestCSVExport(ReportsTestCase):
    """Test CSV export generation, headers, escaping, formula injection mitigation, and date filtering."""

    def test_csv_export_success_and_headers(self):
        """CSV export returns proper attachment filename, content-type, and expected columns."""
        self.login_as('karan@example.com')
        response = self.client.get('/reports/export?month=10&year=2026')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'text/csv')
        self.assertIn('attachment; filename="expense_tracker_report_2026_10.csv"', response.headers.get('Content-Disposition', ''))

        # Check CSV header row
        csv_file = io.StringIO(response.data.decode('utf-8'))
        reader = csv.reader(csv_file)
        header = next(reader)
        expected_header = ['Date', 'Title', 'Category', 'Type', 'Amount', 'Payment Method', 'Description']
        self.assertEqual(header, expected_header)

    def test_csv_export_rows_and_numeric_amounts(self):
        """CSV exported amounts must be numeric without currency symbols."""
        tx = Transaction(
            user_id=self.user1.id,
            category_id=self.cat_food.id,
            amount=Decimal('1499.50'),
            title='Supermarket',
            transaction_date=date(2026, 10, 12),
            payment_method='Credit Card',
            description='Weekly supplies'
        )
        db.session.add(tx)
        db.session.commit()

        self.login_as('karan@example.com')
        response = self.client.get('/reports/export?month=10&year=2026')
        csv_file = io.StringIO(response.data.decode('utf-8'))
        reader = csv.reader(csv_file)
        next(reader)  # Skip header
        row = next(reader)

        self.assertEqual(row[0], '2026-10-12')
        self.assertEqual(row[1], 'Supermarket')
        self.assertEqual(row[2], 'Food')
        self.assertEqual(row[3], 'Expense')
        self.assertEqual(row[4], '1499.50')  # Pure numeric, no ₹ symbol
        self.assertEqual(row[5], 'Credit Card')
        self.assertEqual(row[6], 'Weekly supplies')

    def test_csv_export_commas_quotes_and_newlines(self):
        """CSV writer properly handles fields containing commas, double quotes, and newlines."""
        tx = Transaction(
            user_id=self.user1.id,
            category_id=self.cat_food.id,
            amount=Decimal('450.00'),
            title='Coffee, Snacks & "Special" Items',
            transaction_date=date(2026, 10, 14),
            payment_method='Cash',
            description="Item 1: Tea,\nItem 2: Samosa\nNote: 'Hot & Fresh'"
        )
        db.session.add(tx)
        db.session.commit()

        self.login_as('karan@example.com')
        response = self.client.get('/reports/export?month=10&year=2026')
        csv_file = io.StringIO(response.data.decode('utf-8'))
        reader = csv.reader(csv_file)
        next(reader)  # Header
        row = next(reader)

        self.assertEqual(row[1], 'Coffee, Snacks & "Special" Items')
        self.assertEqual(row[6], "Item 1: Tea,\nItem 2: Samosa\nNote: 'Hot & Fresh'")

    def test_csv_formula_injection_protection(self):
        """Neutralize dangerous formula characters (=, +, -, @, and leading whitespace)."""
        malicious_inputs = [
            ("=SUM(A1:A10)", "'=SUM(A1:A10)"),
            ("+123456", "'+123456"),
            ("-CalcExecution", "'-CalcExecution"),
            ("@cmd|' /C calc'!A0", "'@cmd|' /C calc'!A0"),
            ("   =2+5", "'   =2+5"),
            ("\t=DDE", "'\t=DDE")
        ]

        for i, (mal_title, expected_sanitized) in enumerate(malicious_inputs):
            tx = Transaction(
                user_id=self.user1.id,
                category_id=self.cat_transport.id,
                amount=Decimal('100.00'),
                title=mal_title,
                transaction_date=date(2026, 10, 1 + i),
                payment_method='Cash',
                description=mal_title
            )
            db.session.add(tx)
        db.session.commit()

        self.login_as('karan@example.com')
        response = self.client.get('/reports/export?month=10&year=2026')
        csv_file = io.StringIO(response.data.decode('utf-8'))
        reader = csv.reader(csv_file)
        next(reader)  # Header

        rows = list(reader)
        # Transactions are ordered newest date first
        rows_by_title = {r[1]: r for r in rows}

        for mal_title, expected_sanitized in malicious_inputs:
            self.assertIn(expected_sanitized, rows_by_title, f"Formula injection not neutralized for: {mal_title}")
            self.assertEqual(rows_by_title[expected_sanitized][6], expected_sanitized)

    def test_csv_export_date_filtering(self):
        """CSV export contains only records within the selected calendar month."""
        tx_target = Transaction(
            user_id=self.user1.id,
            category_id=self.cat_food.id,
            amount=Decimal('500.00'),
            title='In October',
            transaction_date=date(2026, 10, 15),
            payment_method='Cash'
        )
        tx_outside = Transaction(
            user_id=self.user1.id,
            category_id=self.cat_food.id,
            amount=Decimal('600.00'),
            title='In September',
            transaction_date=date(2026, 9, 30),
            payment_method='Cash'
        )
        db.session.add_all([tx_target, tx_outside])
        db.session.commit()

        self.login_as('karan@example.com')
        response = self.client.get('/reports/export?month=10&year=2026')
        csv_text = response.data.decode('utf-8')

        self.assertIn('In October', csv_text)
        self.assertNotIn('In September', csv_text)


class TestReportsSecurityAndValidation(ReportsTestCase):
    """Test authentication guards, multi-tenant data isolation, and invalid parameter rejection."""

    def test_unauthenticated_access_redirects(self):
        """Unauthenticated requests to reports and export routes redirect to login."""
        r1 = self.client.get('/reports')
        self.assertEqual(r1.status_code, 302)
        self.assertIn('/login', r1.headers['Location'])

        r2 = self.client.get('/reports/export?month=10&year=2026')
        self.assertEqual(r2.status_code, 302)
        self.assertIn('/login', r2.headers['Location'])

    def test_user_data_isolation(self):
        """User Two cannot view or export User One's transactions."""
        tx1 = Transaction(
            user_id=self.user1.id,
            category_id=self.cat_salary.id,
            amount=Decimal('100000.00'),
            title='Karan Private Income',
            transaction_date=date(2026, 10, 5),
            payment_method='Bank'
        )
        db.session.add(tx1)
        db.session.commit()

        # Login as User 2 (Ananya)
        self.login_as('ananya@example.com')

        # Check Report page
        resp_report = self.client.get('/reports?month=10&year=2026')
        self.assertEqual(resp_report.status_code, 200)
        html = resp_report.data.decode('utf-8')
        self.assertNotIn('Karan Private Income', html)
        self.assertNotIn('₹1,00,000.00', html)

        # Check CSV export
        resp_export = self.client.get('/reports/export?month=10&year=2026')
        self.assertEqual(resp_export.status_code, 200)
        csv_text = resp_export.data.decode('utf-8')
        self.assertNotIn('Karan Private Income', csv_text)
        self.assertNotIn('100000.00', csv_text)

    def test_rejection_of_invalid_month_and_year(self):
        """Server returns 400 Bad Request when month or year parameters are invalid or out of range."""
        self.login_as('karan@example.com')

        invalid_params = [
            {'month': '13', 'year': '2026'},
            {'month': '0', 'year': '2026'},
            {'month': '-1', 'year': '2026'},
            {'month': 'abc', 'year': '2026'},
            {'month': '10', 'year': '1999'},
            {'month': '10', 'year': '2101'},
            {'month': '10', 'year': 'xyz'},
        ]

        for p in invalid_params:
            # Report page rejection
            res_rep = self.client.get('/reports', query_string=p)
            self.assertEqual(res_rep.status_code, 400, f"Reports page did not reject invalid params: {p}")

            # CSV export rejection
            res_exp = self.client.get('/reports/export', query_string=p)
            self.assertEqual(res_exp.status_code, 400, f"CSV export did not reject invalid params: {p}")


if __name__ == '__main__':
    unittest.main()
