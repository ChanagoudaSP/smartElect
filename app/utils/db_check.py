from flask import current_app
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

def verify_db_connection():
    """Verify database connection and log any issues"""
    try:
        # Get SQLAlchemy engine
        engine = current_app.extensions['sqlalchemy'].db.engine
        
        # Test connection with simple query
        with engine.connect() as conn:
            conn.execute(text('SELECT 1'))
            logger.info("Database connection successful")
            return True
            
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
        return False
