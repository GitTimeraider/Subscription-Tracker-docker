from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, FloatField, DateField, SelectField, IntegerField, TextAreaField, BooleanField, ValidationError
from wtforms.validators import DataRequired, Optional, Email, EqualTo, Length, NumberRange
from flask_login import current_user
from app.models import User, PaymentMethod
from app.currency import currency_converter

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])


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
                                 ('insurance', 'Insurances'),
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
    custom_notification_days = IntegerField('Custom notification days (override default)', 
                                          validators=[Optional(), NumberRange(min=1, max=365)],
                                          render_kw={'placeholder': 'Leave blank to use default'})
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
    webhook_notifications = BooleanField('Enable Webhook Notifications')
    notification_days = IntegerField('Days before expiry to send notification', 
                                   validators=[DataRequired(), NumberRange(min=1, max=365)])
    notification_time = SelectField('Daily notification time', 
                                  choices=[(i, f'{i:02d}:00') for i in range(24)],
                                  coerce=int,
                                  validators=[DataRequired()])

class GeneralSettingsForm(FlaskForm):
    currency = SelectField('Preferred Display Currency', validators=[DataRequired()])
    timezone = SelectField('Timezone',
                          choices=[('UTC', 'UTC'), ('US/Eastern', 'Eastern Time'), 
                                 ('US/Central', 'Central Time'), ('US/Mountain', 'Mountain Time'),
                                 ('US/Pacific', 'Pacific Time'), ('Europe/London', 'London'),
                                 ('Europe/Paris', 'Paris'), ('Europe/Berlin', 'Berlin'),
                                 ('Europe/Amsterdam', 'Amsterdam'), ('Asia/Tokyo', 'Tokyo'), 
                                 ('Asia/Shanghai', 'Shanghai')],
                          validators=[DataRequired()])
    preferred_rate_provider = SelectField('Exchange Rate Provider', choices=[
    ('frankfurter','Frankfurter (api.frankfurter.app)'),
    ('floatrates','FloatRates (floatrates.com daily JSON)'),
    ('erapi_open','ER API Open (open.er-api.com)')
    ], validators=[Optional()])
    theme_mode = SelectField('Theme Mode', 
                           choices=[('light', 'Light Mode'), ('dark', 'Dark Mode')], 
                           validators=[DataRequired()])
    accent_color = SelectField('Accent Color',
                             choices=[('blue', 'Blue'), ('purple', 'Purple'), ('green', 'Green'), ('red', 'Red')],
                             validators=[DataRequired()])
    date_format = SelectField('Date Format',
                            choices=[('eu', 'European (DD/MM/YYYY)'), ('us', 'US (MM/DD/YYYY)')],
                            validators=[DataRequired()])
    
    def __init__(self, *args, **kwargs):
        super(GeneralSettingsForm, self).__init__(*args, **kwargs)
        self.currency.choices = currency_converter.get_supported_currencies()
    # Preselect provider if settings exist on the object

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

class AdminUserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    is_admin = BooleanField('Admin User')

class AdminEditUserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    new_password = PasswordField('New Password (leave blank to keep current)', validators=[Optional(), Length(min=6)])
    is_admin = BooleanField('Admin User')

class WebhookForm(FlaskForm):
    name = StringField('Webhook Name', validators=[DataRequired(), Length(min=1, max=100)])
    webhook_type = SelectField('Webhook Type', 
                              choices=[('gotify', 'Gotify'),
                                     ('teams', 'Microsoft Teams'),
                                     ('discord', 'Discord'),
                                     ('slack', 'Slack'),
                                     ('generic', 'Generic JSON')],
                              validators=[DataRequired()])
    url = StringField('Webhook URL', validators=[DataRequired(), Length(min=1, max=500)])
    auth_header = StringField('API Key/Token (optional)', validators=[Optional(), Length(max=200)])
    auth_username = StringField('Username (for Basic Auth)', validators=[Optional(), Length(max=100)])
    auth_password = PasswordField('Password (for Basic Auth)', validators=[Optional(), Length(max=200)])
    custom_headers = TextAreaField('Custom Headers (JSON format)', validators=[Optional()],
                                  render_kw={'placeholder': '{"X-Custom-Header": "value", "Another-Header": "value2"}'})
    is_active = BooleanField('Active', default=True)
    
    def validate_custom_headers(self, field):
        if field.data:
            try:
                import json
                json.loads(field.data)
            except ValueError:
                raise ValidationError('Custom headers must be valid JSON format')
    
    def validate_url(self, field):
        if not (field.data.startswith('http://') or field.data.startswith('https://')):
            raise ValidationError('URL must start with http:// or https://')
