import os
import logging
from logging.handlers import RotatingFileHandler
from werkzeug.serving import WSGIRequestHandler

def setup_logging():
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Console handler with streamlined formatting
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler with rotation
    log_file = os.path.join(log_dir, 'smart_elect.log')
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=1024 * 1024,  # 1MB
        backupCount=5,
        delay=True
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

# Set up logging first
setup_logging()

# Create Flask app
from app import create_app
app = create_app()

if __name__ == '__main__':
    # Configure server
    WSGIRequestHandler.protocol_version = "HTTP/1.1"
    # Run app with optimized settings
    app.run(
        host='127.0.0.1',
        port=5000,
        debug=True,
        threaded=True,
        processes=1
    )