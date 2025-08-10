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
    fixer_api_key = db.Column(db.String(100))  # API key for currency conversion

class PaymentMethod(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    payment_type = db.Column(db.String(50), nullable=False)
    last_four = db.Column(db.String(4), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship back to user
    user = db.relationship('User', backref=db.backref('payment_methods', lazy=True))
    
    def __repr__(self):
        return f'<PaymentMethod {self.name}>'

class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    company = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50))  # Software, Hardware, Entertainment, etc.
    cost = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='USD')  # Currency of the subscription
    billing_cycle = db.Column(db.String(50), nullable=False)  # daily, weekly, monthly, yearly, custom
    custom_days = db.Column(db.Integer)  # For custom billing cycles (deprecated, use custom_period_value)
    custom_period_type = db.Column(db.String(10), default='days')  # 'days', 'months', 'years'
    custom_period_value = db.Column(db.Integer)  # For custom billing cycles
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)  # None means infinite
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    payment_method_id = db.Column(db.Integer, db.ForeignKey('payment_method.id'))
    last_notification = db.Column(db.Date)
    notes = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    payment_method = db.relationship('PaymentMethod', backref='subscriptions')

    def get_monthly_cost(self, target_currency=None, exchange_rates=None):
        """Calculate monthly cost based on billing cycle, optionally converted to target currency"""
        monthly_cost = 0
        
        if self.billing_cycle == 'daily':
            monthly_cost = self.cost * 30
        elif self.billing_cycle == 'weekly':
            monthly_cost = self.cost * 4.33  # Average weeks per month
        elif self.billing_cycle == 'bi-weekly':
            monthly_cost = self.cost * 2.17  # Every 2 weeks
        elif self.billing_cycle == 'monthly':
            monthly_cost = self.cost
        elif self.billing_cycle == 'bi-monthly':
            monthly_cost = self.cost / 2  # Every 2 months
        elif self.billing_cycle == 'quarterly':
            monthly_cost = self.cost / 3  # Every 3 months
        elif self.billing_cycle == 'semi-annually':
            monthly_cost = self.cost / 6  # Every 6 months
        elif self.billing_cycle == 'yearly':
            monthly_cost = self.cost / 12
        elif self.billing_cycle == 'custom':
            if self.custom_period_value and self.custom_period_type:
                if self.custom_period_type == 'days':
                    monthly_cost = (self.cost / self.custom_period_value) * 30.44  # Average days per month
                elif self.custom_period_type == 'months':
                    monthly_cost = self.cost / self.custom_period_value
                elif self.custom_period_type == 'years':
                    monthly_cost = self.cost / (self.custom_period_value * 12)
            elif self.custom_days:  # Fallback for backward compatibility
                monthly_cost = (self.cost / self.custom_days) * 30.44  # Average days per month
        
        # Convert currency if needed
        if target_currency and target_currency != self.currency and exchange_rates:
            if self.currency in exchange_rates and target_currency in exchange_rates:
                # Convert from subscription currency to USD, then to target currency
                if self.currency != 'USD':
                    monthly_cost = monthly_cost / exchange_rates[self.currency]
                if target_currency != 'USD':
                    monthly_cost = monthly_cost * exchange_rates[target_currency]
        
        return monthly_cost

    def get_yearly_cost(self, target_currency=None, exchange_rates=None):
        """Calculate yearly cost"""
        return self.get_monthly_cost(target_currency, exchange_rates) * 12

    def get_cost_in_currency(self, target_currency=None, exchange_rates=None):
        """Get the raw cost converted to target currency"""
        cost = self.cost
        
        if target_currency and target_currency != self.currency and exchange_rates:
            if self.currency in exchange_rates and target_currency in exchange_rates:
                # Convert from subscription currency to USD, then to target currency
                if self.currency != 'USD':
                    cost = cost / exchange_rates[self.currency]
                if target_currency != 'USD':
                    cost = cost * exchange_rates[target_currency]
        
        return cost

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

    def get_monthly_cost_in_currency(self, target_currency):
        """Get monthly cost converted to target currency using currency converter"""
        from app.currency import currency_converter
        
        monthly_cost = self.get_monthly_cost()
        if not target_currency or target_currency == self.currency:
            return monthly_cost
        
        return currency_converter.convert_amount(monthly_cost, self.currency or 'USD', target_currency)
    
    def get_yearly_cost_in_currency(self, target_currency):
        """Get yearly cost converted to target currency using currency converter"""
        from app.currency import currency_converter
        
        yearly_cost = self.get_yearly_cost()
        if not target_currency or target_currency == self.currency:
            return yearly_cost
        
        return currency_converter.convert_amount(yearly_cost, self.currency or 'USD', target_currency)
