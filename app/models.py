from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True)
    password_hash = db.Column(db.String(200))
    subscriptions = db.relationship('Subscription', backref='user', lazy=True)
    settings = db.relationship('UserSettings', backref='user', uselist=False, lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class UserSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    email_notifications = db.Column(db.Boolean, default=True)
    notification_days = db.Column(db.Integer, default=7)
    currency = db.Column(db.String(3), default='USD')
    timezone = db.Column(db.String(50), default='UTC')

class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    company = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50))  # Software, Hardware, Entertainment, etc.
    cost = db.Column(db.Float, nullable=False)
    billing_cycle = db.Column(db.String(50), nullable=False)  # daily, weekly, monthly, yearly, custom
    custom_days = db.Column(db.Integer)  # For custom billing cycles
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)  # None means infinite
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    last_notification = db.Column(db.Date)
    notes = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)

    def get_monthly_cost(self):
        """Calculate monthly cost based on billing cycle"""
        if self.billing_cycle == 'daily':
            return self.cost * 30
        elif self.billing_cycle == 'weekly':
            return self.cost * 4.33  # Average weeks per month
        elif self.billing_cycle == 'bi-weekly':
            return self.cost * 2.17  # Every 2 weeks
        elif self.billing_cycle == 'monthly':
            return self.cost
        elif self.billing_cycle == 'bi-monthly':
            return self.cost / 2  # Every 2 months
        elif self.billing_cycle == 'quarterly':
            return self.cost / 3  # Every 3 months
        elif self.billing_cycle == 'semi-annually':
            return self.cost / 6  # Every 6 months
        elif self.billing_cycle == 'yearly':
            return self.cost / 12
        elif self.billing_cycle == 'custom' and self.custom_days:
            return (self.cost / self.custom_days) * 30.44  # Average days per month
        return 0

    def get_yearly_cost(self):
        """Calculate yearly cost"""
        return self.get_monthly_cost() * 12

    def is_expiring_soon(self, days_ahead=7):
        """Check if subscription is expiring within specified days"""
        if not self.end_date:
            return False
        
        from datetime import datetime, timedelta
        check_date = datetime.now().date() + timedelta(days=days_ahead)
        return self.end_date <= check_date and self.end_date >= datetime.now().date()

    def days_until_expiry(self):
        """Get days until expiry"""
        if not self.end_date:
            return None
        
        from datetime import datetime
        delta = self.end_date - datetime.now().date()
        return delta.days if delta.days >= 0 else 0
