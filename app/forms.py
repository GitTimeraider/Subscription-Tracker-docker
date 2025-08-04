from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, FloatField, DateField, SelectField, IntegerField
from wtforms.validators import DataRequired, Optional

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])

class SubscriptionForm(FlaskForm):
    name = StringField('Subscription Name', validators=[DataRequired()])
    company = StringField('Company', validators=[DataRequired()])
    cost = FloatField('Cost', validators=[DataRequired()])
    billing_cycle = SelectField('Billing Cycle', 
                               choices=[('monthly', 'Monthly'), 
                                      ('yearly', 'Yearly'), 
                                      ('custom', 'Custom')],
                               validators=[DataRequired()])
    custom_days = IntegerField('Custom Days', validators=[Optional()])
    start_date = DateField('Start Date', validators=[DataRequired()])
    end_date = DateField('End Date', validators=[Optional()])
