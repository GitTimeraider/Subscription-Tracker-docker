from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, FloatField, DateField, SelectField, IntegerField, TextAreaField, BooleanField, ValidationError
from wtforms.validators import DataRequired, Optional, Email, EqualTo, Length, NumberRange
from flask_login import current_user
from app.models import User, PaymentMethod
from app.currency import currency_converter

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Repeat Password', validators=[DataRequired(), EqualTo('password')])
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already exists. Please choose a different one.')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered. Please choose a different one.')

class SubscriptionForm(FlaskForm):
    name = StringField('Subscription Name', validators=[DataRequired()])
    company = StringField('Company', validators=[DataRequired()])
    category = SelectField('Category', 
                          choices=[('software', 'Software'), 
                                 ('hardware', 'Hardware'),
                                 ('entertainment', 'Entertainment'),
                                 ('utilities', 'Utilities'),
                                 ('cloud_services', 'Cloud Services'),
                                 ('news_media', 'News & Media'),
                                 ('education', 'Education'),
                                 ('fitness', 'Fitness & Health'),
                                 ('gaming', 'Gaming'),
                                 ('other', 'Other')],
                          validators=[Optional()])
    cost = FloatField('Cost', validators=[DataRequired(), NumberRange(min=0)])
    currency = SelectField('Currency', validators=[DataRequired()])
    billing_cycle = SelectField('Billing Cycle', 
                               choices=[('daily', 'Daily'),
                                      ('weekly', 'Weekly'),
                                      ('bi-weekly', 'Bi-weekly (Every 2 weeks)'),
                                      ('monthly', 'Monthly'), 
                                      ('bi-monthly', 'Bi-monthly (Every 2 months)'),
                                      ('quarterly', 'Quarterly (Every 3 months)'),
                                      ('semi-annually', 'Semi-annually (Every 6 months)'),
                                      ('yearly', 'Yearly'), 
                                      ('custom', 'Custom')],
                               validators=[DataRequired()])
    custom_period_type = SelectField('Custom Period Type',
                                   choices=[('days', 'Days'),
                                          ('months', 'Months'),
                                          ('years', 'Years')],
                                   validators=[Optional()])
    custom_period_value = IntegerField('Custom Period Value', validators=[Optional(), NumberRange(min=1)])
    payment_method_id = SelectField('Payment Method', coerce=int, validators=[Optional()])
    start_date = DateField('Start Date', validators=[DataRequired()])
    end_date = DateField('End Date (Leave blank for infinite)', validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional()])
    
    def __init__(self, *args, **kwargs):
        super(SubscriptionForm, self).__init__(*args, **kwargs)
        
        # Set currency choices
        self.currency.choices = currency_converter.get_supported_currencies()
        
        # Set payment method choices
        if current_user.is_authenticated:
            payment_methods = PaymentMethod.query.filter_by(user_id=current_user.id).all()
            self.payment_method_id.choices = [(0, 'Select Payment Method')] + [(pm.id, pm.name) for pm in payment_methods]
        else:
            self.payment_method_id.choices = [(0, 'Select Payment Method')]

class UserSettingsForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    current_password = PasswordField('Current Password (required for changes)', validators=[Optional()])
    new_password = PasswordField('New Password', validators=[Optional(), Length(min=6)])
    confirm_password = PasswordField('Confirm New Password', validators=[Optional(), EqualTo('new_password')])
    
    def validate_username(self, username):
        if username.data != current_user.username:
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('Username already exists. Please choose a different one.')
    
    def validate_email(self, email):
        if email.data != current_user.email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('Email already registered. Please choose a different one.')

class NotificationSettingsForm(FlaskForm):
    email_notifications = BooleanField('Enable Email Notifications')
    notification_days = IntegerField('Days before expiry to send notification', 
                                   validators=[DataRequired(), NumberRange(min=1, max=365)])

class GeneralSettingsForm(FlaskForm):
    currency = SelectField('Preferred Display Currency', validators=[DataRequired()])
    fixer_api_key = StringField('APILayer API Key (for currency conversion)', validators=[Optional()])
    timezone = SelectField('Timezone',
                          choices=[('UTC', 'UTC'), ('US/Eastern', 'Eastern Time'), 
                                 ('US/Central', 'Central Time'), ('US/Mountain', 'Mountain Time'),
                                 ('US/Pacific', 'Pacific Time'), ('Europe/London', 'London'),
                                 ('Europe/Paris', 'Paris'), ('Europe/Berlin', 'Berlin'),
                                 ('Europe/Amsterdam', 'Amsterdam'), ('Asia/Tokyo', 'Tokyo'), 
                                 ('Asia/Shanghai', 'Shanghai')],
                          validators=[DataRequired()])
    
    def __init__(self, *args, **kwargs):
        super(GeneralSettingsForm, self).__init__(*args, **kwargs)
        self.currency.choices = currency_converter.get_supported_currencies()

class EmailSettingsForm(FlaskForm):
    mail_server = StringField('SMTP Server', validators=[Optional()])
    mail_port = IntegerField('SMTP Port', validators=[Optional(), NumberRange(min=1, max=65535)])
    mail_use_tls = BooleanField('Use TLS')
    mail_username = StringField('Email Username', validators=[Optional(), Email()])
    mail_password = PasswordField('Email Password', validators=[Optional()])
    mail_from = StringField('From Email Address', validators=[Optional(), Email()])

class PaymentMethodForm(FlaskForm):
    name = StringField('Payment Method Name', validators=[DataRequired(), Length(min=1, max=100)])
    payment_type = SelectField('Type', 
                      choices=[('credit_card', 'Credit Card'),
                             ('debit_card', 'Debit Card'),
                             ('bank_account', 'Bank Account'),
                             ('paypal', 'PayPal'),
                             ('apple_pay', 'Apple Pay'),
                             ('google_pay', 'Google Pay'),
                             ('other', 'Other')],
                      validators=[DataRequired()])
    last_four = StringField('Last 4 Digits (optional)', validators=[Optional(), Length(max=4)])
    notes = TextAreaField('Notes', validators=[Optional()])
