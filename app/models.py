from datetime import datetime, date
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True)
    password_hash = db.Column(db.String(200))
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    subscriptions = db.relationship('Subscription', backref='user', lazy=True)

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
    
    # Notification settings
    email_notifications = db.Column(db.Boolean, default=True)
    notification_days = db.Column(db.Integer, default=7)
    
    # SMTP settings for email notifications
    mail_server = db.Column(db.String(100))
    mail_port = db.Column(db.Integer, default=587)
    mail_use_tls = db.Column(db.Boolean, default=True)
    mail_username = db.Column(db.String(100))
    mail_password = db.Column(db.String(100))
    mail_from = db.Column(db.String(100))
    
    # General settings
    currency = db.Column(db.String(3), default='EUR')
    timezone = db.Column(db.String(50), default='UTC')
    unirate_api_key = db.Column(db.String(100))  # Deprecated: no longer used (ECB rates)
    preferred_rate_provider = db.Column(db.String(30))  # 'exchangerate_host','frankfurter','ecb'
    
    # Theme settings
    theme_mode = db.Column(db.String(10), default='light')  # 'light' or 'dark'
    accent_color = db.Column(db.String(10), default='purple')  # 'blue', 'purple', etc.
    
    # Relationship
    user = db.relationship('User', backref=db.backref('settings', uselist=False))

    def __repr__(self):
        return f'<UserSettings {self.user_id}>'

class ExchangeRate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    base_currency = db.Column(db.String(3), nullable=False, default='EUR')
    provider = db.Column(db.String(40), nullable=False, default='legacy')  # data source identifier
    rates_json = db.Column(db.Text, nullable=False)  # JSON string of exchange rates
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('date', 'base_currency', 'provider', name='uq_rate_date_base_provider'),
    )
    
    def __repr__(self):
        return f'<ExchangeRate {self.date} base:{self.base_currency} provider:{self.provider}>'
    
    @classmethod
    def get_latest_rates(cls, base_currency='EUR', provider=None):
        """Get the latest exchange rates for today for a specific provider (if given)."""
        today = date.today()
        query = cls.query.filter_by(date=today, base_currency=base_currency)
        if provider:
            query = query.filter_by(provider=provider)
        rate_record = query.first()
        if rate_record:
            import json
            return json.loads(rate_record.rates_json)
        return None
    
    @classmethod
    def save_rates(cls, rates, base_currency='EUR', provider='unknown'):
        """Save exchange rates for today for the given provider. Upsert semantics."""
        import json
        today = date.today()
        existing_rate = cls.query.filter_by(date=today, base_currency=base_currency, provider=provider).first()
        if existing_rate:
            existing_rate.rates_json = json.dumps(rates)
            existing_rate.created_at = datetime.utcnow()
        else:
            new_rate = cls(
                date=today,
                base_currency=base_currency,
                provider=provider,
                rates_json=json.dumps(rates)
            )
            db.session.add(new_rate)
        db.session.commit()

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
    currency = db.Column(db.String(3), default='EUR')  # Currency of the subscription
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
        
        # Convert currency if needed (assumes exchange_rates are based on EUR)
        if target_currency and target_currency != self.currency and exchange_rates:
            base_currency = 'EUR'
            if self.currency in exchange_rates and target_currency in exchange_rates:
                # Convert source -> base
                if self.currency == base_currency:
                    amount_in_base = monthly_cost
                else:
                    amount_in_base = monthly_cost / exchange_rates[self.currency]
                # Base -> target
                if target_currency == base_currency:
                    monthly_cost = amount_in_base
                else:
                    monthly_cost = amount_in_base * exchange_rates[target_currency]
        
        return monthly_cost

    def get_yearly_cost(self, target_currency=None, exchange_rates=None):
        """Calculate yearly cost"""
        return self.get_monthly_cost(target_currency, exchange_rates) * 12

    def get_cost_in_currency(self, target_currency=None, exchange_rates=None):
        """Get the raw cost converted to target currency"""
        cost = self.cost
        
        if target_currency and target_currency != self.currency and exchange_rates:
            base_currency = 'EUR'
            if self.currency in exchange_rates and target_currency in exchange_rates:
                if self.currency == base_currency:
                    amount_in_base = cost
                else:
                    amount_in_base = cost / exchange_rates[self.currency]
                if target_currency == base_currency:
                    cost = amount_in_base
                else:
                    cost = amount_in_base * exchange_rates[target_currency]
        
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
        """Get monthly cost converted to target currency using currency converter with timeout protection"""
        from app.currency import currency_converter
        
        if not target_currency or target_currency == self.currency:
            return self.get_monthly_cost()
        
        # Use cached rates to avoid API calls during subscription operations
        try:
            from flask import g
            if not hasattr(g, '_eur_rates_cache'):
                # Try to get from cache first, only fetch if absolutely necessary
                cached_rates = None
                try:
                    from app.models import ExchangeRate
                    from datetime import date
                    latest = ExchangeRate.query.filter_by(date=date.today(), base_currency='EUR').first()
                    if latest:
                        import json
                        cached_rates = json.loads(latest.rates_json)
                except Exception:
                    pass
                
                if cached_rates:
                    from decimal import Decimal
                    g._eur_rates_cache = {k: Decimal(str(v)) for k, v in cached_rates.items()}
                else:
                    # Fallback - fetch rates but with timeout protection
                    try:
                        g._eur_rates_cache = currency_converter.get_exchange_rates('EUR') or {}
                    except Exception:
                        # If all else fails, use fallback rates
                        g._eur_rates_cache = currency_converter._get_fallback_rates('EUR') or {}
            rates = g._eur_rates_cache
        except Exception:
            # Final fallback - use static conversion or return original cost
            try:
                rates = currency_converter.get_exchange_rates('EUR') or {}
            except Exception:
                rates = currency_converter._get_fallback_rates('EUR') or {}
        
        base_currency = 'EUR'
        monthly_cost_source = self.get_monthly_cost()
        return currency_converter.convert_amount(monthly_cost_source, self.currency or base_currency, target_currency, rates=rates, base_currency=base_currency)
    
    def get_yearly_cost_in_currency(self, target_currency):
        """Get yearly cost converted to target currency using currency converter with timeout protection"""
        from app.currency import currency_converter
        
        if not target_currency or target_currency == self.currency:
            return self.get_yearly_cost()
        
        # Use same caching strategy as monthly cost
        try:
            from flask import g
            if not hasattr(g, '_eur_rates_cache'):
                # Try to get from cache first, only fetch if absolutely necessary
                cached_rates = None
                try:
                    from app.models import ExchangeRate
                    from datetime import date
                    latest = ExchangeRate.query.filter_by(date=date.today(), base_currency='EUR').first()
                    if latest:
                        import json
                        cached_rates = json.loads(latest.rates_json)
                except Exception:
                    pass
                
                if cached_rates:
                    from decimal import Decimal
                    g._eur_rates_cache = {k: Decimal(str(v)) for k, v in cached_rates.items()}
                else:
                    # Fallback - fetch rates but with timeout protection
                    try:
                        g._eur_rates_cache = currency_converter.get_exchange_rates('EUR') or {}
                    except Exception:
                        # If all else fails, use fallback rates
                        g._eur_rates_cache = currency_converter._get_fallback_rates('EUR') or {}
            rates = g._eur_rates_cache
        except Exception:
            # Final fallback - use static conversion or return original cost
            try:
                rates = currency_converter.get_exchange_rates('EUR') or {}
            except Exception:
                rates = currency_converter._get_fallback_rates('EUR') or {}
        
        base_currency = 'EUR'
        yearly_cost_source = self.get_yearly_cost()
        return currency_converter.convert_amount(yearly_cost_source, self.currency or base_currency, target_currency, rates=rates, base_currency=base_currency)
