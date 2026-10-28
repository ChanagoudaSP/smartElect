import logging
import logging.handlers

from datetime import datetime, timedelta

from app import create_app, db
from app.models.models import User, Election


def test_mysql_unavailable_falls_back_to_sqlite(monkeypatch):
    import mysql.connector

    def raise_operational_error(*args, **kwargs):
        raise mysql.connector.errors.OperationalError("2055", "Lost connection to MySQL server")

    monkeypatch.setattr(mysql.connector, 'connect', raise_operational_error)

    app = create_app()

    assert app.config['SQLALCHEMY_DATABASE_URI'].startswith('sqlite:///')


class TestConfig:
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = 'test-secret'
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False


def test_register_accepts_email_password_only():
    app = create_app(TestConfig)

    with app.test_client() as client:
        response = client.post(
            '/auth/register',
            data={
                'email': 'plainuser@example.com',
                'password': 'SecurePass123',
                'confirm_password': 'SecurePass123',
                'first_name': 'Plain',
                'last_name': 'User',
                'national_id': 'ABCD1234',
            },
            follow_redirects=False,
        )

        assert response.status_code == 302
        assert response.location.endswith('/auth/login')

        user = User.query.filter_by(email='plainuser@example.com').first()
        assert user is not None
        assert user.check_password('SecurePass123')

        db.session.remove()


def test_login_accepts_email_password_only():
    app = create_app(TestConfig)

    with app.app_context():
        user = User(
            email='loginuser@example.com',
            first_name='Login',
            last_name='User',
            national_id='AAAA1234',
            is_verified=True,
        )
        user.set_password('SecurePass123')
        db.session.add(user)
        db.session.commit()

    with app.test_client() as client:
        response = client.post(
            '/auth/login',
            data={
                'email': 'loginuser@example.com',
                'password': 'SecurePass123',
            },
            follow_redirects=False,
        )

        assert response.status_code == 302
        assert response.location.endswith('/')


def test_upcoming_election_is_visible_on_user_dashboard():
    app = create_app(TestConfig)

    with app.app_context():
        user = User(
            email='futureuser@example.com',
            first_name='Future',
            last_name='User',
            national_id='FUTU1234',
            is_verified=True,
        )
        user.set_password('SecurePass123')
        db.session.add(user)
        db.session.commit()

        election = Election(
            title='Future Election',
            description='A new poll scheduled for users to preview.',
            start_date=datetime.utcnow() + timedelta(days=2),
            end_date=datetime.utcnow() + timedelta(days=5),
            is_active=True,
        )
        db.session.add(election)
        db.session.commit()

    with app.test_client() as client:
        login_response = client.post(
            '/auth/login',
            data={'email': 'futureuser@example.com', 'password': 'SecurePass123'},
            follow_redirects=False,
        )
        assert login_response.status_code == 302

        dashboard_response = client.get('/dashboard')
        assert dashboard_response.status_code == 200
        assert b'Future Election' in dashboard_response.data


def test_default_localhost_config_allows_http_sessions():
    app = create_app()

    assert app.config['SESSION_COOKIE_SECURE'] is False
    assert app.config['REMEMBER_COOKIE_SECURE'] is False


def test_logging_uses_non_rotating_file_handler():
    app = create_app(TestConfig)

    assert any(isinstance(handler, logging.FileHandler) for handler in app.logger.handlers)
    assert not any(
        isinstance(handler, logging.handlers.RotatingFileHandler)
        for handler in app.logger.handlers
    )
