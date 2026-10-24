"""Unit tests for Indian Rupee (INR) formatting and password visibility toggle markup."""

import unittest
from decimal import Decimal
from app import create_app
from app.extensions import db
from app.models import User, Category, Transaction, seed_categories
from app.utils import format_inr


class TestCurrencyINR(unittest.TestCase):
    """Test format_inr formatting utility according to Indian numbering system."""

    def test_format_inr_values(self):
        """Verify Indian number grouping across different orders of magnitude."""
        self.assertEqual(format_inr(150), '₹150.00')
        self.assertEqual(format_inr(Decimal('150.00')), '₹150.00')
        self.assertEqual(format_inr(1250), '₹1,250.00')
        self.assertEqual(format_inr(Decimal('1250.00')), '₹1,250.00')
        self.assertEqual(format_inr(12500), '₹12,500.00')
        self.assertEqual(format_inr(Decimal('12500.00')), '₹12,500.00')
        self.assertEqual(format_inr(125000), '₹1,25,000.00')
        self.assertEqual(format_inr(Decimal('125000.00')), '₹1,25,000.00')
        self.assertEqual(format_inr(Decimal('1234567.89')), '₹12,34,567.89')

    def test_format_inr_zero_and_negative(self):
        """Verify format_inr handles zero, negative values, and None."""
        self.assertEqual(format_inr(0), '₹0.00')
        self.assertEqual(format_inr(Decimal('0.00')), '₹0.00')
        self.assertEqual(format_inr(None), '₹0.00')
        self.assertEqual(format_inr(-1250.50), '-₹1,250.50')
        self.assertEqual(format_inr(Decimal('-125000.00')), '-₹1,25,000.00')

    def test_format_inr_without_symbol(self):
        """Verify format_inr without currency symbol."""
        self.assertEqual(format_inr(125000, include_symbol=False), '1,25,000.00')


class TestPasswordVisibilityMarkup(unittest.TestCase):
    """Test presence of password visibility toggle controls on login and register pages."""

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

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_login_page_has_password_toggle(self):
        """Login page has password toggle button with accessible label and initial password type."""
        response = self.client.get('/login')
        self.assertEqual(response.status_code, 200)
        html = response.data.decode('utf-8')

        # Input must be type="password" by default
        self.assertIn('type="password"', html)
        self.assertIn('id="password"', html)

        # Toggle button targeting password input
        self.assertIn('password-toggle-btn', html)
        self.assertIn('data-target="password"', html)
        self.assertIn('aria-label="Show password"', html)
        self.assertIn('icon-eye', html)
        self.assertIn('icon-eye-slash', html)

    def test_register_page_has_independent_toggles(self):
        """Register page has independent toggles for password and confirm_password."""
        response = self.client.get('/register')
        self.assertEqual(response.status_code, 200)
        html = response.data.decode('utf-8')

        # Both inputs must be present and hidden by default
        self.assertIn('id="password"', html)
        self.assertIn('id="confirm_password"', html)

        # Both toggle buttons must exist
        self.assertIn('data-target="password"', html)
        self.assertIn('data-target="confirm_password"', html)

    def test_transaction_form_and_list_currency_symbol(self):
        """Transaction form and list render with ₹ (INR)."""
        # Register and login
        self.client.post('/register', data={
            'name': 'Ravi Kumar',
            'email': 'ravi@example.com',
            'password': 'password123',
            'confirm_password': 'password123',
        })
        self.client.post('/login', data={'email': 'ravi@example.com', 'password': 'password123'})

        # Check form label
        res_form = self.client.get('/transactions/new')
        self.assertIn('Amount (₹)', res_form.data.decode('utf-8'))
        self.assertNotIn('Amount ($)', res_form.data.decode('utf-8'))

        # Create transaction and check list display
        cat = Category.query.filter_by(name='Salary', type='income').first()
        self.client.post('/transactions/new', data={
            'title': 'Monthly Salary',
            'transaction_type': 'income',
            'category_id': cat.id,
            'amount': '125000.00',
            'payment_method': 'Bank Transfer',
            'transaction_date': '2026-10-01',
        })

        res_list = self.client.get('/transactions')
        html_list = res_list.data.decode('utf-8')
        # Must show +₹1,25,000.00 and no dollar signs
        self.assertIn('+₹1,25,000.00', html_list)
        self.assertNotIn('$', html_list)


class TestThemeToggle(unittest.TestCase):
    """Test presence of dark/light theme toggle button and theme initialization attributes."""

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

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_base_template_has_theme_toggle_and_attributes(self):
        """Theme toggle button and data-bs-theme attribute are present in base template."""
        res = self.client.get('/login')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')

        self.assertIn('data-bs-theme="light"', html)
        self.assertIn('id="themeToggleBtn"', html)
        self.assertIn('theme-icon-sun', html)
        self.assertIn('theme-icon-moon', html)


if __name__ == '__main__':
    unittest.main()
