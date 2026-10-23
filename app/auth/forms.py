"""Authentication forms for registration and login."""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError, Regexp
from app.models import User

# Standard RFC-compliant email regex pattern that requires zero external packages
EMAIL_REGEX = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'


def strip_filter(value):
    """Strip leading and trailing whitespace from string input."""
    return value.strip() if isinstance(value, str) else value


class RegistrationForm(FlaskForm):
    """User registration form with server-side validation."""
    name = StringField(
        'Full Name',
        filters=[strip_filter],
        validators=[
            DataRequired(message="Name is required."),
            Length(min=2, max=100, message="Name must be between 2 and 100 characters.")
        ]
    )
    email = StringField(
        'Email Address',
        filters=[strip_filter],
        validators=[
            DataRequired(message="Email is required."),
            Regexp(EMAIL_REGEX, message="Please enter a valid email address."),
            Length(max=120, message="Email must not exceed 120 characters.")
        ]
    )
    password = PasswordField(
        'Password',
        validators=[
            DataRequired(message="Password is required."),
            Length(min=8, max=128, message="Password must be at least 8 characters long.")
        ]
    )
    confirm_password = PasswordField(
        'Confirm Password',
        validators=[
            DataRequired(message="Please confirm your password."),
            EqualTo('password', message="Passwords must match.")
        ]
    )
    submit = SubmitField('Create Account')

    def validate_email(self, field):
        """Ensure email uniqueness using normalized lowercase email."""
        normalized_email = field.data.strip().lower() if field.data else ''
        existing_user = User.query.filter_by(email=normalized_email).first()
        if existing_user:
            raise ValidationError("This email address is already registered.")


class LoginForm(FlaskForm):
    """User login form."""
    email = StringField(
        'Email Address',
        filters=[strip_filter],
        validators=[
            DataRequired(message="Email is required."),
            Regexp(EMAIL_REGEX, message="Please enter a valid email address.")
        ]
    )
    password = PasswordField(
        'Password',
        validators=[
            DataRequired(message="Password is required.")
        ]
    )
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')
