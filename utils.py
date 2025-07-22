from functools import wraps
from flask import request, current_app
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging
import os

# Setup logging
def setup_logging(app):
    log_level = getattr(logging, app.config['LOG_LEVEL'].upper())
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Only add file handler if not running on Vercel
    if not os.environ.get('VERCEL'):
        if not os.path.exists('logs'):
            os.makedirs('logs')
        file_handler = logging.FileHandler('logs/printpal.log')
        file_handler.setLevel(log_level)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        app.logger.addHandler(file_handler)
    
# Setup rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["50 per minute"],
    storage_uri="memory://"
)

def init_limiter(app):
    limiter.init_app(app)
    
# Rate limit decorators
def login_limit():
    return limiter.limit("50 per minute") 