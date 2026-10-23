"""Authentication route controllers for registration, login, and logout."""

from urllib.parse import urlsplit
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user, login_required
from app.extensions import db
from app.models import User
from app.auth import auth_bp
from app.auth.forms import RegistrationForm, LoginForm


def is_safe_url(target):
    """Validate that the redirect URL is a safe local path to prevent open redirects."""
    if not target:
        return False
    test_url = urlsplit(target)
    # Reject absolute URLs with foreign host or scheme
    if test_url.scheme or test_url.netloc:
        return False
    # Ensure it's a relative path starting with single '/'
    return target.startswith('/') and not target.startswith('//') and not target.startswith('\\')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Handle new user registration with server-side validation and password hashing."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = RegistrationForm()
    if form.validate_on_submit():
        normalized_email = form.email.data.strip().lower()
        user = User(
            name=form.name.data.strip(),
            email=normalized_email
        )
        user.set_password(form.password.data)

        try:
            db.session.add(user)
            db.session.commit()
            flash("Your account has been created successfully! Please sign in.", "success")
            return redirect(url_for('auth.login'))
        except Exception:
            db.session.rollback()
            flash("An unexpected error occurred while creating your account. Please try again.", "danger")

    return render_template('auth/register.html', form=form)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user authentication with generic error feedback and safe redirect."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = LoginForm()
    if form.validate_on_submit():
        normalized_email = form.email.data.strip().lower()
        user = User.query.filter_by(email=normalized_email).first()

        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            flash(f"Welcome back, {user.name}!", "success")
            next_page = request.args.get('next')
            if not is_safe_url(next_page):
                next_page = url_for('main.index')
            return redirect(next_page)
        else:
            flash("Invalid email or password.", "danger")

    return render_template('auth/login.html', form=form)


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """Handle user logout via CSRF-protected POST request."""
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for('auth.login'))
