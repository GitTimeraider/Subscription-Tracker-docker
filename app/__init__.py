from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'

    from app.routes import main
    app.register_blueprint(main)

    with app.app_context():
        db.create_all()

        # Create default admin user if none exists
        from app.models import User, UserSettings
        if not User.query.first():
            default_user = User(username='admin', email='admin@example.com')
            default_user.set_password('changeme')
            db.session.add(default_user)
            db.session.commit()
            
            # Create default settings for admin user
            admin_settings = UserSettings(user_id=default_user.id)
            db.session.add(admin_settings)
            db.session.commit()
            
            print("Default admin user created: username='admin', password='changeme'")
            print("Please change the default password immediately!")

    # Start scheduler for email notifications
    from app.email import start_scheduler
    start_scheduler(app)

    return app
