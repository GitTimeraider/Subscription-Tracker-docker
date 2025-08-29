import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from app.models import Subscription, User, UserSettings
from app import db
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

def create_email_body(user, subscriptions):
    """Create HTML email body for subscription notifications"""
    
    html_body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .header {{ background-color: #007bff; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; }}
            .subscription {{ background-color: #f8f9fa; border-left: 4px solid #007bff; margin: 10px 0; padding: 15px; }}
            .urgent {{ border-left-color: #dc3545; }}
            .warning {{ border-left-color: #ffc107; }}
            .footer {{ background-color: #f8f9fa; padding: 15px; text-align: center; color: #666; }}
            .cost {{ font-weight: bold; color: #007bff; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🔔 Subscription Expiry Notifications</h1>
        </div>
        
        <div class="content">
            <p>Hello {user.username},</p>
            <p>You have {len(subscriptions)} subscription(s) expiring soon:</p>
    """
    
    for subscription in subscriptions:
        days_left = subscription.days_until_expiry()
        
        if days_left <= 3:
            css_class = "subscription urgent"
            urgency = "🚨 URGENT"
        elif days_left <= 7:
            css_class = "subscription warning"
            urgency = "⚠️ WARNING"
        else:
            css_class = "subscription"
            urgency = "ℹ️ NOTICE"
        
        html_body += f"""
            <div class="{css_class}">
                <h3>{urgency} - {subscription.name}</h3>
                <p><strong>Company:</strong> {subscription.company}</p>
                <p><strong>Category:</strong> {subscription.category or 'Not specified'}</p>
                <p><strong>Cost:</strong> <span class="cost">${subscription.cost:.2f}</span> ({subscription.billing_cycle})</p>
                <p><strong>Monthly Cost:</strong> <span class="cost">${subscription.get_monthly_cost():.2f}</span></p>
                <p><strong>Expires in:</strong> {days_left} day(s) ({subscription.end_date})</p>
                {f'<p><strong>Notes:</strong> {subscription.notes}</p>' if subscription.notes else ''}
            </div>
        """
    
    html_body += """
        <p>Please review these subscriptions and renew them if you wish to continue.</p>
        <p>You can manage your subscriptions by logging into your Subscription Tracker dashboard.</p>
        </div>
        
        <div class="footer">
            <p>This is an automated notification from your Subscription Tracker.</p>
            <p>You can modify your notification preferences in your account settings.</p>
        </div>
    </body>
    </html>
    """
    
    return html_body

def send_expiry_notification(app, user, subscriptions):
    """Send email notification for expiring subscriptions"""
    with app.app_context():
        # Check email configuration
        if not all([app.config['MAIL_SERVER'], app.config['MAIL_USERNAME'], 
                   app.config['MAIL_PASSWORD']]):
            print("❌ Email configuration incomplete:")
            print(f"   MAIL_SERVER: {'✓' if app.config['MAIL_SERVER'] else '✗'}")
            print(f"   MAIL_USERNAME: {'✓' if app.config['MAIL_USERNAME'] else '✗'}")
            print(f"   MAIL_PASSWORD: {'✓' if app.config['MAIL_PASSWORD'] else '✗'}")
            return False

        # Use user's email if available, otherwise use configured email
        to_email = user.email or app.config['MAIL_USERNAME']
        
        print(f"📧 Preparing notification for {user.username} ({to_email})")
        print(f"   📊 {len(subscriptions)} subscription(s) expiring soon")
        
        subject = f"🔔 {len(subscriptions)} Subscription(s) Expiring Soon"
        
        # Create multipart message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = app.config['MAIL_FROM'] or app.config['MAIL_USERNAME']
        msg['To'] = to_email

        # Create plain text version
        text_body = f"""
        Hello {user.username},

        You have {len(subscriptions)} subscription(s) expiring soon:

        """
        
        for subscription in subscriptions:
            days_left = subscription.days_until_expiry()
            text_body += f"""
        - {subscription.name} ({subscription.company})
          Expires in {days_left} day(s) on {subscription.end_date}
          Cost: ${subscription.cost:.2f} ({subscription.billing_cycle})
          Monthly Cost: ${subscription.get_monthly_cost():.2f}
        
        """
        
        text_body += """
        Please review these subscriptions and renew them if you wish to continue.
        You can manage your subscriptions by logging into your Subscription Tracker dashboard.
        
        This is an automated notification from your Subscription Tracker.
        """

        # Create HTML version
        html_body = create_email_body(user, subscriptions)

        # Add both parts to the message
        part1 = MIMEText(text_body, 'plain')
        part2 = MIMEText(html_body, 'html')
        
        msg.attach(part1)
        msg.attach(part2)

        try:
            # Log connection attempt
            print(f"🔌 Connecting to {app.config['MAIL_SERVER']}:{app.config['MAIL_PORT']}")
            
            # Use SSL for port 465, TLS for other ports
            if app.config['MAIL_PORT'] == 465:
                # Port 465 uses implicit SSL
                print("🔒 Using SSL connection (port 465)")
                server = smtplib.SMTP_SSL(app.config['MAIL_SERVER'], app.config['MAIL_PORT'])
            else:
                # Other ports use explicit TLS or plain connection
                print(f"🔐 Using {'TLS' if app.config['MAIL_USE_TLS'] else 'plain'} connection")
                server = smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT'])
                if app.config['MAIL_USE_TLS']:
                    server.starttls()
            
            with server:
                print("🔑 Authenticating...")
                server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
                print("📨 Sending email...")
                server.send_message(msg)

                # Update last notification date for all subscriptions
                for subscription in subscriptions:
                    subscription.last_notification = datetime.now().date()
                db.session.commit()
                
                print(f"✅ Notification sent to {user.username} for {len(subscriptions)} subscriptions")
                return True
                
        except smtplib.SMTPAuthenticationError as e:
            print(f"❌ SMTP Authentication failed for {user.username}: {e}")
            print("🔍 Check MAIL_USERNAME and MAIL_PASSWORD")
            return False
        except smtplib.SMTPConnectError as e:
            print(f"❌ SMTP Connection failed for {user.username}: {e}")
            print("🔍 Check MAIL_SERVER and MAIL_PORT")
            return False
        except smtplib.SMTPException as e:
            print(f"❌ SMTP error for {user.username}: {e}")
            return False
        except Exception as e:
            print(f"❌ Failed to send email to {user.username}: {e}")
            return False

def check_expiring_subscriptions(app):
    """Check for expiring subscriptions and send notifications"""
    with app.app_context():
        print(f"🔍 Checking expiring subscriptions at {datetime.now()}")
        
        # Get all users with notification settings
        users = User.query.all()
        total_notifications = 0
        
        for user in users:
            user_settings = user.settings or UserSettings()
            
            # Skip if user has disabled email notifications
            if not user_settings.email_notifications:
                print(f"⏭️  Skipping {user.username} - notifications disabled")
                continue
                
            days_before = user_settings.notification_days
            check_date = datetime.now().date() + timedelta(days=days_before)

            # Find subscriptions that are:
            # 1. Expiring within the notification window
            # 2. Haven't been notified today
            # 3. Are still active
            subscriptions = Subscription.query.filter(
                Subscription.user_id == user.id,
                Subscription.is_active == True,
                Subscription.end_date.isnot(None),
                Subscription.end_date <= check_date,
                Subscription.end_date >= datetime.now().date(),
                (Subscription.last_notification == None) | 
                (Subscription.last_notification < datetime.now().date())
            ).all()

            if subscriptions:
                print(f"📧 Sending notification to {user.username} for {len(subscriptions)} subscriptions")
                success = send_expiry_notification(app, user, subscriptions)
                if success:
                    total_notifications += 1
                else:
                    print(f"❌ Failed to send notification to {user.username}")
            else:
                print(f"✅ No notifications needed for {user.username}")
        
        print(f"📊 Notification check completed. Sent {total_notifications} notifications.")

def start_scheduler(app):
    """Start the background scheduler for checking expiring subscriptions"""
    scheduler = BackgroundScheduler()
    
    # Check every 6 hours instead of daily for more timely notifications
    scheduler.add_job(
        func=lambda: check_expiring_subscriptions(app),
        trigger="interval",
        hours=6,
        id='check_subscriptions',
        replace_existing=True
    )
    
    # Also add a daily job at 9 AM for primary notifications
    scheduler.add_job(
        func=lambda: check_expiring_subscriptions(app),
        trigger="cron",
        hour=9,
        minute=0,
        id='daily_check_subscriptions',
        replace_existing=True
    )
    
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown())
    print("Email notification scheduler started")
