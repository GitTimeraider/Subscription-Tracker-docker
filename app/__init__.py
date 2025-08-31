from flask import Flask, g, request, render_template
import time
import signal
from contextlib import contextmanager
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()

class TimeoutError(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutError("Operation timed out")

@contextmanager
def timeout(seconds):
    """Context manager for operation timeout"""
    # Set the signal handler and a alarm
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        # Restore the old signal handler and cancel the alarm
        signal.signal(signal.SIGALRM, old_handler)
        signal.alarm(0)

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'

    # Add custom Jinja2 filters for date formatting based on user preference
    @app.template_filter('user_date')
    def user_date_filter(date_obj):
        """Format date based on user's preference (EU: DD/MM/YYYY or US: MM/DD/YYYY)"""
        if date_obj is None:
            return ''
        
        # Get user's date format preference
        try:
            from flask_login import current_user
            if current_user.is_authenticated and hasattr(current_user, 'settings') and current_user.settings:
                date_format = current_user.settings.date_format or 'eu'
            else:
                date_format = 'eu'  # Default to European format
        except:
            date_format = 'eu'  # Fallback to European format
        
        if date_format == 'us':
            return date_obj.strftime('%m/%d/%Y')
        else:
            return date_obj.strftime('%d/%m/%Y')
    
    @app.template_filter('user_datetime')
    def user_datetime_filter(datetime_obj):
        """Format datetime based on user's preference"""
        if datetime_obj is None:
            return ''
        
        # Get user's date format preference
        try:
            from flask_login import current_user
            if current_user.is_authenticated and hasattr(current_user, 'settings') and current_user.settings:
                date_format = current_user.settings.date_format or 'eu'
            else:
                date_format = 'eu'  # Default to European format
        except:
            date_format = 'eu'  # Fallback to European format
        
        if date_format == 'us':
            return datetime_obj.strftime('%m/%d/%Y %H:%M:%S')
        else:
            return datetime_obj.strftime('%d/%m/%Y %H:%M:%S')
    
    @app.template_filter('user_datetime_utc')
    def user_datetime_utc_filter(datetime_obj):
        """Format datetime with UTC based on user's preference"""
        if datetime_obj is None:
            return ''
        
        # Get user's date format preference
        try:
            from flask_login import current_user
            if current_user.is_authenticated and hasattr(current_user, 'settings') and current_user.settings:
                date_format = current_user.settings.date_format or 'eu'
            else:
                date_format = 'eu'  # Default to European format
        except:
            date_format = 'eu'  # Fallback to European format
        
        if date_format == 'us':
            return datetime_obj.strftime('%m/%d/%Y %H:%M:%S UTC')
        else:
            return datetime_obj.strftime('%d/%m/%Y %H:%M:%S UTC')

    # Keep the old filters for backward compatibility
    @app.template_filter('eu_date')
    def eu_date_filter(date_obj):
        """Format date as DD/MM/YYYY (European format)"""
        if date_obj is None:
            return ''
        return date_obj.strftime('%d/%m/%Y')
    
    @app.template_filter('eu_datetime')
    def eu_datetime_filter(datetime_obj):
        """Format datetime as DD/MM/YYYY HH:MM:SS (European format)"""
        if datetime_obj is None:
            return ''
        return datetime_obj.strftime('%d/%m/%Y %H:%M:%S')
    
    @app.template_filter('eu_datetime_utc')
    def eu_datetime_utc_filter(datetime_obj):
        """Format datetime as DD/MM/YYYY HH:MM:SS UTC (European format)"""
        if datetime_obj is None:
            return ''
        return datetime_obj.strftime('%d/%m/%Y %H:%M:%S UTC')

    # Add template context processor to make user date format available in templates
    @app.context_processor
    def inject_user_date_format():
        """Make user's date format preference available in all templates"""
        try:
            from flask_login import current_user
            if current_user.is_authenticated and hasattr(current_user, 'settings') and current_user.settings:
                date_format = current_user.settings.date_format or 'eu'
                if date_format == 'us':
                    return {
                        'user_date_format': 'us',
                        'date_format_display': 'MM/DD/YYYY',
                        'date_placeholder': 'MM/DD/YYYY'
                    }
                else:
                    return {
                        'user_date_format': 'eu',
                        'date_format_display': 'DD/MM/YYYY',
                        'date_placeholder': 'DD/MM/YYYY'
                    }
            else:
                return {
                    'user_date_format': 'eu',
                    'date_format_display': 'DD/MM/YYYY',
                    'date_placeholder': 'DD/MM/YYYY'
                }
        except:
            return {
                'user_date_format': 'eu',
                'date_format_display': 'DD/MM/YYYY',
                'date_placeholder': 'DD/MM/YYYY'
            }

    from app.routes import main
    app.register_blueprint(main)

    with app.app_context():
        db.create_all()

        # Create default admin user if no admin users exist
        from app.models import User, UserSettings
        admin_exists = User.query.filter_by(is_admin=True).first()
        if not admin_exists:
            default_user = User(username='admin', email='admin@example.com', is_admin=True)
            default_user.set_password('changeme')
            db.session.add(default_user)
            db.session.commit()
            
            # Create default settings for admin user
            admin_settings = UserSettings(user_id=default_user.id)
            db.session.add(admin_settings)
            db.session.commit()
            
            print("Default admin user created: username='admin', password='changeme'")
            print("Please change the default password immediately!")

    # Lazy scheduler + perf timer combined (Flask 3 removed before_first_request)
    @app.before_request
    def _pre_request_hooks():
        # Start perf timer if enabled
        if app.config.get('PERFORMANCE_LOGGING') or request.environ.get('PERFORMANCE_LOGGING'):
            g._req_start_ts = time.time()

        # Skip heavy startup for static assets and auth pages
        path = request.path or ''
        if path.startswith('/static') or path in ('/login','/','/favicon.ico'):
            return

        # Set database timeout to prevent long-running queries
        if hasattr(db.engine, 'pool') and hasattr(db.engine.pool, '_timeout'):
            db.engine.pool._timeout = 30  # 30 second timeout for database operations

        # Only start scheduler after a non-auth (post-login) request to reduce cold-login latency
        if not getattr(app, '_scheduler_started', False):
            try:
                from flask_login import current_user
                if current_user.is_authenticated:
                    from app.email import start_scheduler
                    start_scheduler(app)
                    app._scheduler_started = True
            except Exception as e:
                app.logger.error(f"Failed to start scheduler: {e}")

    @app.after_request
    def _perf_timer_end(response):
        start_ts = getattr(g, '_req_start_ts', None)
        if start_ts is not None:
            elapsed_ms = (time.time() - start_ts) * 1000
            # Only log slow requests > 200ms
            if elapsed_ms > 200:
                app.logger.warning(f"Slow request {request.method} {request.path} took {elapsed_ms:.1f} ms")
            else:
                app.logger.debug(f"Request {request.method} {request.path} {elapsed_ms:.1f} ms")
        return response

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        app.logger.error(f"Internal server error: {error}")
        return render_template('500.html'), 500

    @app.errorhandler(TimeoutError)
    def timeout_error(error):
        db.session.rollback()
        app.logger.error(f"Request timeout: {error}")
        from flask import flash, redirect, url_for
        flash('The operation timed out. Please try again.', 'error')
        return redirect(url_for('main.dashboard'))

    return app
