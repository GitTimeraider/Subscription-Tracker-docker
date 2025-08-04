import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from app.models import Subscription
from app import db
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

def send_expiry_notification(app, subscription):
    with app.app_context():
        if not all([app.config['MAIL_SERVER'], app.config['MAIL_USERNAME'], 
                   app.config['MAIL_PASSWORD'], app.config['MAIL_FROM']]):
            print("Email configuration incomplete")
            return

        subject = f"Subscription Expiry Notice: {subscription.name}"
        body = f"""
        Your subscription is expiring soon!

        Subscription: {subscription.name}
        Company: {subscription.company}
        End Date: {subscription.end_date}
        Monthly Cost: ${subscription.get_monthly_cost():.2f}

        Please renew your subscription if you wish to continue.
        """

        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = app.config['MAIL_FROM']
        msg['To'] = app.config['MAIL_USERNAME']

        try:
            with smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT']) as server:
                if app.config['MAIL_USE_TLS']:
                    server.starttls()
                server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
                server.send_message(msg)

                subscription.last_notification = datetime.now().date()
                db.session.commit()
        except Exception as e:
            print(f"Failed to send email: {e}")

def check_expiring_subscriptions(app):
    with app.app_context():
        days_before = app.config['DAYS_BEFORE_EXPIRY']
        check_date = datetime.now().date() + timedelta(days=days_before)

        subscriptions = Subscription.query.filter(
            Subscription.end_date <= check_date,
            Subscription.end_date >= datetime.now().date(),
            (Subscription.last_notification == None) | 
            (Subscription.last_notification < datetime.now().date())
        ).all()

        for subscription in subscriptions:
            send_expiry_notification(app, subscription)

def start_scheduler(app):
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=lambda: check_expiring_subscriptions(app),
        trigger="interval",
        hours=24,
        id='check_subscriptions',
        replace_existing=True
    )
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown())
