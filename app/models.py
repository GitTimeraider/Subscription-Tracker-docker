from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200))
    subscriptions = db.relationship('Subscription', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    company = db.Column(db.String(100), nullable=False)
    cost = db.Column(db.Float, nullable=False)
    billing_cycle = db.Column(db.String(50), nullable=False)  # monthly, yearly, custom
    custom_days = db.Column(db.Integer)  # For custom billing cycles
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    last_notification = db.Column(db.Date)

    def get_monthly_cost(self):
        if self.billing_cycle == 'monthly':
            return self.cost
        elif self.billing_cycle == 'yearly':
            return self.cost / 12
        elif self.billing_cycle == 'custom' and self.custom_days:
            return (self.cost / self.custom_days) * 30
        return 0
