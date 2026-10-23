"""Automated test suite for user authentication, session security, and authorization."""

import unittest
from unittest.mock import patch
from app import create_app
from app.extensions import db
from app.models import User


class AuthTestCase(unittest.TestCase):
    """Test case setup for authentication tests with an in-memory database."""

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

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def register_user(self, name='Jane Doe', email='jane@example.com', password='password123', confirm_password='password123'):
        """Helper to post registration data."""
        return self.client.post('/register', data={
            'name': name,
            'email': email,
            'password': password,
            'confirm_password': confirm_password,
        }, follow_redirects=True)

    def login_user(self, email='jane@example.com', password='password123', next_url=None):
        """Helper to post login data."""
        url = '/login'
        if next_url:
            url += f'?next={next_url}'
        return self.client.post(url, data={
            'email': email,
            'password': password,
        }, follow_redirects=False)


class TestRegistration(AuthTestCase):
    """Registration workflow, validation, and normalization tests."""

    def test_successful_registration(self):
        """Valid registration creates a user in the database and redirects to login."""
        response = self.register_user()
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Your account has been created successfully', response.data)

        user = User.query.filter_by(email='jane@example.com').first()
        self.assertIsNotNone(user)
        self.assertEqual(user.name, 'Jane Doe')
        self.assertTrue(user.check_password('password123'))
        self.assertNotEqual(user.password_hash, 'password123')

    def test_missing_or_invalid_fields(self):
        """Registration fails when required fields are missing or email is malformed."""
        # Missing name
        res = self.register_user(name='')
        self.assertIn(b'Name is required.', res.data)

        # Invalid email format
        res = self.register_user(email='not-an-email')
        self.assertIn(b'Please enter a valid email address.', res.data)

        # Password shorter than 8 chars
        res = self.register_user(password='short', confirm_password='short')
        self.assertIn(b'Password must be at least 8 characters long.', res.data)

    def test_password_mismatch(self):
        """Registration fails when password and confirm_password do not match."""
        response = self.register_user(password='password123', confirm_password='differentpassword')
        self.assertIn(b'Passwords must match.', response.data)
        self.assertIsNone(User.query.filter_by(email='jane@example.com').first())

    def test_duplicate_email_and_case_normalization(self):
        """Emails must be normalized to lowercase and duplicates rejected."""
        # Register user with mixed-case email
        self.register_user(email='Jane.Doe@EXAMPLE.COM')
        user = User.query.filter_by(email='jane.doe@example.com').first()
        self.assertIsNotNone(user)

        # Attempt duplicate registration with lowercase email
        res = self.register_user(email='jane.doe@example.com')
        self.assertIn(b'This email address is already registered.', res.data)

        # Attempt duplicate registration with mixed-case and whitespace
        res = self.register_user(email='  JANE.DOE@example.com  ')
        self.assertIn(b'This email address is already registered.', res.data)

    def test_database_rollback_on_registration_error(self):
        """Database rollback is performed cleanly if a commit fails during registration."""
        with patch.object(db.session, 'commit', side_effect=Exception("Simulated DB failure")):
            response = self.register_user(name='Error Test', email='error@example.com')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'An unexpected error occurred while creating your account.', response.data)
            self.assertIsNone(User.query.filter_by(email='error@example.com').first())


class TestLoginAndSession(AuthTestCase):
    """Login authentication, invalid credentials, and session management."""

    def setUp(self):
        super().setUp()
        user = User(name='John Smith', email='john@example.com')
        user.set_password('correctpassword')
        db.session.add(user)
        db.session.commit()

    def test_successful_login(self):
        """User can log in with valid credentials and receives a session."""
        response = self.login_user(email='john@example.com', password='correctpassword')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, '/')

        # Follow redirect and verify welcome banner and user display
        follow_res = self.client.get(response.location)
        self.assertEqual(follow_res.status_code, 200)
        self.assertIn(b'Welcome back, John Smith!', follow_res.data)
        self.assertIn(b'Logged in as <strong>John Smith</strong>', follow_res.data)

    def test_login_email_case_insensitivity(self):
        """User can log in using mixed-case email."""
        response = self.login_user(email='  JOHN@example.COM  ', password='correctpassword')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, '/')

    def test_invalid_credentials_generic_message(self):
        """Generic error message is displayed for wrong password or non-existent user."""
        # Wrong password
        res = self.client.post('/login', data={'email': 'john@example.com', 'password': 'wrongpassword'}, follow_redirects=True)
        self.assertIn(b'Invalid email or password.', res.data)

        # Non-existent user
        res = self.client.post('/login', data={'email': 'nonexistent@example.com', 'password': 'password123'}, follow_redirects=True)
        self.assertIn(b'Invalid email or password.', res.data)

    def test_authenticated_user_redirected_from_login_and_register(self):
        """Logged-in users visiting /login or /register are redirected to dashboard."""
        self.login_user(email='john@example.com', password='correctpassword')

        res_login = self.client.get('/login')
        self.assertEqual(res_login.status_code, 302)
        self.assertEqual(res_login.location, '/')

        res_register = self.client.get('/register')
        self.assertEqual(res_register.status_code, 302)
        self.assertEqual(res_register.location, '/')

    def test_logout(self):
        """User can log out via POST, clearing session and redirecting to login."""
        self.login_user(email='john@example.com', password='correctpassword')

        # Logout via POST
        res = self.client.post('/logout')
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.location, '/login')

        follow_res = self.client.get(res.location)
        self.assertIn(b'You have been logged out.', follow_res.data)

        # Accessing dashboard afterwards should redirect to login
        dash_res = self.client.get('/')
        self.assertEqual(dash_res.status_code, 302)
        self.assertIn('/login', dash_res.location)


class TestRouteGuarding(AuthTestCase):
    """Protected routes redirect unauthenticated users."""

    def test_unauthenticated_access_redirects(self):
        """Protected views require authentication and redirect to login."""
        protected_routes = ['/', '/transactions', '/budgets', '/reports']
        for route in protected_routes:
            response = self.client.get(route)
            self.assertEqual(response.status_code, 302)
            self.assertIn('/login', response.location)

    def test_authenticated_access_succeeds(self):
        """Authenticated users can access protected views."""
        user = User(name='Active User', email='active@example.com')
        user.set_password('activepassword')
        db.session.add(user)
        db.session.commit()

        self.login_user(email='active@example.com', password='activepassword')

        protected_routes = ['/', '/transactions', '/budgets', '/reports']
        for route in protected_routes:
            response = self.client.get(route)
            self.assertEqual(response.status_code, 200)


class TestSecurityFeatures(AuthTestCase):
    """Safe redirect checks and CSRF protection."""

    def setUp(self):
        super().setUp()
        user = User(name='Sec User', email='sec@example.com')
        user.set_password('secpassword')
        db.session.add(user)
        db.session.commit()

    def test_safe_next_parameter_redirect(self):
        """Relative local URLs are accepted for the next redirect parameter."""
        res = self.login_user(email='sec@example.com', password='secpassword', next_url='/transactions')
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.location, '/transactions')

    def test_unsafe_next_parameter_rejected(self):
        """External and malicious redirect URLs are sanitized back to the dashboard."""
        unsafe_targets = [
            'http://evil.com',
            'https://evil.com/phishing',
            '//evil.com',
            '\\\\evil.com',
            'javascript:alert(1)',
        ]
        for target in unsafe_targets:
            res = self.login_user(email='sec@example.com', password='secpassword', next_url=target)
            self.assertEqual(res.status_code, 302)
            self.assertEqual(res.location, '/')

    def test_csrf_protection_enabled(self):
        """State-changing requests without CSRF token are blocked when CSRF is enabled."""
        csrf_app = create_app({
            'TESTING': True,
            'WTF_CSRF_ENABLED': True,
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'SECRET_KEY': 'csrf-test-key',
        })
        with csrf_app.app_context():
            db.create_all()
            client = csrf_app.test_client()

            # Attempt registration without CSRF token
            response = client.post('/register', data={
                'name': 'No CSRF',
                'email': 'nocsrf@example.com',
                'password': 'password123',
                'confirm_password': 'password123',
            })
            # Flask-WTF rejects POST without CSRF with HTTP 400
            self.assertEqual(response.status_code, 400)


if __name__ == '__main__':
    unittest.main()
