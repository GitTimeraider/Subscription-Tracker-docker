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

    from app.routes import main
    app.register_blueprint(main)

    with app.app_context():
        db.create_all()

        # Create default user if none exists
        from app.models import User
        if not User.query.first():
            default_user = User(username='admin')
            default_user.set_password('changeme')
            db.session.add(default_user)
            db.session.commit()

    # Start scheduler for email notifications
    from app.email import start_scheduler
    start_scheduler(app)

    return app
