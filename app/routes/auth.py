import logging
import re

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app import db
from app.models.models import User

# Configure logging
logger = logging.getLogger(__name__)

bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        national_id = request.form.get('national_id', '').strip().upper()

        if not email or not password or not first_name or not last_name or not national_id:
            flash('Please fill in all required fields.')
            return redirect(url_for('auth.register'))

        if password != confirm_password:
            flash('Passwords do not match.')
            return redirect(url_for('auth.register'))

        if not re.fullmatch(r'[A-Z0-9]{8,12}', national_id):
            flash('Voter ID must be 8-12 characters, uppercase letters and numbers only (e.g., AB1234CD)')
            return redirect(url_for('auth.register'))

        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return redirect(url_for('auth.register'))

        if User.query.filter_by(national_id=national_id).first():
            flash('Voter ID already registered')
            return redirect(url_for('auth.register'))

        if not re.fullmatch(r"[A-Za-z]+", first_name):
            flash('First name must contain only letters (A-Z, a-z)')
            return redirect(url_for('auth.register'))
        if not re.fullmatch(r"[A-Za-z]+", last_name):
            flash('Last name must contain only letters (A-Z, a-z)')
            return redirect(url_for('auth.register'))

        user = User(
            email=email,
            first_name=first_name,
            last_name=last_name,
            national_id=national_id,
            is_verified=True,
        )
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        flash('Registration successful')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        user = User.query.filter_by(email=email).first()
        logger.info(f"Login attempt for email: {email}")

        if not user or not user.check_password(password):
            logger.error("Invalid email or password")
            flash('Invalid email or password')
            return render_template('auth/login.html')

        logger.info("Password verification successful")
        login_user(user)

        if user.is_admin:
            logger.info("Admin user detected, redirecting to admin dashboard")
            return redirect(url_for('admin.dashboard'))

        next_page = request.args.get('next')
        logger.info(f"Redirecting to: {next_page or url_for('main.index')}")
        return redirect(next_page or url_for('main.index'))

    return render_template('auth/login.html')

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()
        if not user:
            flash('No account found with that email.', 'danger')
            return redirect(url_for('auth.forgot_password'))
        # In a real app, generate a token and send email. Here, redirect to reset form.
        return redirect(url_for('auth.reset_password', email=email))
    return render_template('auth/forgot_password.html')

@bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    email = request.args.get('email')
    if not email:
        flash('Invalid or missing email for password reset.', 'danger')
        return redirect(url_for('auth.forgot_password'))
    user = User.query.filter_by(email=email).first()
    if not user:
        flash('No account found with that email.', 'danger')
        return redirect(url_for('auth.forgot_password'))
    if request.method == 'POST':
        password = request.form['password']
        confirm = request.form['confirm_password']
        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('auth.reset_password', email=email))
        user.set_password(password)
        db.session.commit()
        flash('Password reset successful. You can now log in.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', email=email)

