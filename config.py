import os
from datetime import timedelta

# Neon PostgreSQL Configuration
NEON_DB = {
    'host': 'ep-still-star-a8wkzw4n-pooler.eastus2.azure.neon.tech',
    'database': 'neondb',
    'user': 'neondb_owner',
    'password': 'npg_0Iah7FKctiyJ'
}

# Construct Database URL
DEFAULT_DB_URL = f"postgresql://{NEON_DB['user']}:{NEON_DB['password']}@{NEON_DB['host']}/{NEON_DB['database']}"

class Config:
    # Basic Flask config
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY') or 'dev_key_123'
    
    # SQLAlchemy config with Neon PostgreSQL
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or DEFAULT_DB_URL
    if SQLALCHEMY_DATABASE_URI.startswith('postgres://'):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgres://', 'postgresql://')
    
    # Add SSL requirement for Neon
    if 'neon.tech' in SQLALCHEMY_DATABASE_URI and '?' not in SQLALCHEMY_DATABASE_URI:
        SQLALCHEMY_DATABASE_URI += '?sslmode=require'
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'max_overflow': 2,
        'pool_timeout': 30,
        'pool_recycle': 1800,
    }
    
    # Flask-Login config
    REMEMBER_COOKIE_DURATION = timedelta(days=14)
    REMEMBER_COOKIE_SECURE = True
    REMEMBER_COOKIE_HTTPONLY = True
    
    # Security config
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    PERMANENT_SESSION_LIFETIME = timedelta(days=1)
    
    # Rate limiting
    RATELIMIT_DEFAULT = "100 per day"
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL', "memory://")
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')

    # Vercel-specific settings
    if os.environ.get('VERCEL'):
        PREFERRED_URL_SCHEME = 'https'
        SERVER_NAME = os.environ.get('VERCEL_URL')
    
class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False

class ProductionConfig(Config):
    DEBUG = False
    
class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:postgres@localhost/printpal_test'
    WTF_CSRF_ENABLED = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
} 