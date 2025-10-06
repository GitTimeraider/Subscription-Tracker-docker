import os
from datetime import timedelta

def get_engine_options():
    """Get database engine options based on DATABASE_URL"""
    database_url = os.environ.get('DATABASE_URL') or 'sqlite:///subscriptions.db'
    
    if 'sqlite' in database_url.lower():
        # SQLite-specific settings
        return {
            'pool_timeout': 10,
            'pool_recycle': 3600,
            'pool_pre_ping': True,
            'connect_args': {
                'timeout': 20,
                'check_same_thread': False
            }
        }
    elif 'postgresql' in database_url.lower() or 'postgres' in database_url.lower():
        # PostgreSQL-specific settings (psycopg3 compatible)
        return {
            'pool_size': 10,
            'max_overflow': 20,
            'pool_timeout': 30,
            'pool_recycle': 3600,
            'pool_pre_ping': True,
            'connect_args': {
                'connect_timeout': 10
            }
        }
    elif 'mysql' in database_url.lower() or 'mariadb' in database_url.lower():
        # MySQL/MariaDB-specific settings
        return {
            'pool_size': 10,
            'max_overflow': 20,
            'pool_timeout': 30,
            'pool_recycle': 3600,
            'pool_pre_ping': True,
            'connect_args': {
                'charset': 'utf8mb4'
            }
        }
    else:
        # Default settings for other databases
        return {
            'pool_timeout': 30,
            'pool_recycle': 3600,
            'pool_pre_ping': True
        }

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'mad-hatter-secret-key-change-me'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///subscriptions.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Database connection pool settings
    SQLALCHEMY_ENGINE_OPTIONS = get_engine_options()

    # Email configuration
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_FROM = os.environ.get('MAIL_FROM')

    # Notification settings (fallback defaults)
    DAYS_BEFORE_EXPIRY = int(os.environ.get('DAYS_BEFORE_EXPIRY') or 7)
    
    # Application settings
    ITEMS_PER_PAGE = int(os.environ.get('ITEMS_PER_PAGE') or 20)
    
    # Security settings
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None  # Never expire CSRF tokens
    
    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)  # Sessions last 7 days
