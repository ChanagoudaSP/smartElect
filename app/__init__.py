import pymysql
pymysql.install_as_MySQLdb()

from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv
import os
import logging
from config import Config

# Load environment variables from .env file
load_dotenv()

db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()
csrf = CSRFProtect()


def _sqlite_uri():
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    return f"sqlite:///{os.path.join(project_root, 'smart_elect.db')}"


def _mysql_available(config):
    uri = config.get('SQLALCHEMY_DATABASE_URI', '')
    if not uri or uri.startswith('sqlite'):
        return True

    try:
        import mysql.connector

        conn = mysql.connector.connect(
            host=config.get('DB_HOST', 'localhost'),
            user=config.get('DB_USER', 'root'),
            password=config.get('DB_PASSWORD', 'root1'),
            database=config.get('DB_NAME', 'evoting_db'),
            connection_timeout=3,
            autocommit=True,
        )
        conn.close()
        return True
    except Exception:
        return False


@login_manager.user_loader
def load_user(user_id):
    from app.models.models import User
    return User.query.get(int(user_id))

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    if app.config.get('SQLALCHEMY_DATABASE_URI', '').startswith('mysql') and not _mysql_available(app.config):
        app.config['SQLALCHEMY_DATABASE_URI'] = _sqlite_uri()
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {}
        app.logger.warning('MySQL connection unavailable; falling back to SQLite database for local development.')
    
    # Initialize Flask extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    mail.init_app(app)
    
    # Register template filters
    from app.utils.template_filters import register_template_filters
    register_template_filters(app)
    
    # Set up logging
    if not app.debug:
        os.makedirs('logs', exist_ok=True)
        app.logger.handlers.clear()
        app.logger.propagate = False

        file_handler = logging.FileHandler('logs/smart_elect.log')
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Smart-Elect startup')
    
    with app.app_context():
        # Register blueprints
        from app.routes import auth, main, admin, notifications
        app.register_blueprint(auth.bp)
        app.register_blueprint(main.bp)
        app.register_blueprint(admin.bp)
        app.register_blueprint(notifications.bp)
        
        # Register CLI commands
        from app.cli import create_admin
        app.cli.add_command(create_admin)

        db.create_all()
        
        # Register error handlers
        @app.errorhandler(500)
        def internal_error(error):
            db.session.rollback()
            app.logger.error('Server Error: %s', str(error))
            return render_template('errors/500.html'), 500

        @app.errorhandler(404)
        def not_found_error(error):
            return render_template('errors/404.html'), 404

        return app