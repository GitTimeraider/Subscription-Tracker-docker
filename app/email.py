import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from app.models import Subscription, User, UserSettings
from app import db
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

def format_date_for_user(date_obj, user):
    """Format date based on user's date format preference"""
    if not date_obj:
        return 'N/A'
    
    # Get user's date format preference
    try:
        if user and hasattr(user, 'settings') and user.settings:
            date_format = getattr(user.settings, 'date_format', 'eu') or 'eu'
        else:
            date_format = 'eu'  # Default to European format
    except:
        date_format = 'eu'  # Fallback to European format
    
    if date_format == 'us':
        return date_obj.strftime('%m/%d/%Y')
    else:
        return date_obj.strftime('%d/%m/%Y')

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
                <p><strong>Expires in:</strong> {days_left} day(s) ({format_date_for_user(subscription.end_date, user)})</p>
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
          Expires in {days_left} day(s) on {format_date_for_user(subscription.end_date, user)}
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

                # Update last notification date for the user (not individual subscriptions)
                user_settings = user.settings or UserSettings()
                user_settings.last_notification_sent = datetime.now().date()
                if not user.settings:
                    user_settings.user_id = user.id
                    db.session.add(user_settings)
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
        current_time = datetime.now()
        current_hour = current_time.hour
        print(f"🔍 Checking expiring subscriptions at {current_time} (hour: {current_hour})")
        
        # Get all users with notification settings
        users = User.query.all()
        total_notifications = 0
        
        for user in users:
            user_settings = user.settings or UserSettings()
            
            # Skip if user has disabled email notifications
            if not user_settings.email_notifications:
                print(f"⏭️  Skipping {user.username} - notifications disabled")
                continue
            
            # Check if we already sent a notification today for this user
            today = current_time.date()
            if user_settings.last_notification_sent == today:
                print(f"⏭️  Skipping {user.username} - already notified today")
                continue
            
            # Check if it's the user's preferred notification time (±1 hour window)
            preferred_hour = user_settings.notification_time or 9
            if not (preferred_hour - 1 <= current_hour <= preferred_hour + 1):
                print(f"⏭️  Skipping {user.username} - not their notification time (prefers {preferred_hour}:00, current: {current_hour}:00)")
                continue

            # Find subscriptions expiring based on their individual or default notification days
            expiring_subscriptions = []
            
            for subscription in user.subscriptions:
                if not subscription.is_active or not subscription.end_date:
                    continue
                
                # Get notification days for this specific subscription
                notification_days = subscription.get_notification_days(user_settings)
                check_date = today + timedelta(days=notification_days)
                
                # Check if this subscription is expiring within its notification window
                if subscription.end_date <= check_date and subscription.end_date >= today:
                    expiring_subscriptions.append(subscription)

            if expiring_subscriptions:
                print(f"📧 Sending notification to {user.username} for {len(expiring_subscriptions)} subscriptions at preferred time {preferred_hour}:00")
                success = send_expiry_notification(app, user, expiring_subscriptions)
                if success:
                    total_notifications += 1
                else:
                    print(f"❌ Failed to send notification to {user.username}")
            else:
                print(f"✅ No expiring subscriptions for {user.username}")
        
        print(f"📊 Notification check completed. Sent {total_notifications} notifications.")

def start_scheduler(app):
    """Start the background scheduler for checking expiring subscriptions"""
    scheduler = BackgroundScheduler()
    
    # Check every hour to respect user-specific notification times
    scheduler.add_job(
        func=lambda: check_expiring_subscriptions(app),
        trigger="interval",
        hours=1,
        id='check_subscriptions',
        replace_existing=True
    )
    
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown())
    print("Email notification scheduler started (checking hourly)")

def send_test_email(app, user):
    """Send a test email to verify email configuration"""
    with app.app_context():
        # Check email configuration
        if not all([app.config['MAIL_SERVER'], app.config['MAIL_USERNAME'], 
                   app.config['MAIL_PASSWORD']]):
            return {
                'success': False,
                'message': 'Email configuration incomplete. Please check MAIL_SERVER, MAIL_USERNAME, and MAIL_PASSWORD.'
            }

        # Use user's email if available, otherwise use configured email
        to_email = user.email or app.config['MAIL_USERNAME']
        
        print(f"📧 Sending test email to {user.username} ({to_email})")
        
        subject = "🧪 Test Email - Subscription Tracker"
        
        # Create multipart message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = app.config['MAIL_FROM'] or app.config['MAIL_USERNAME']
        msg['To'] = to_email

        # Create plain text version
        text_body = f"""
Hello {user.username},

This is a test email from your Subscription Tracker application.

If you're receiving this email, your email configuration is working correctly!

Configuration details:
- MAIL_SERVER: {app.config['MAIL_SERVER']}
- MAIL_PORT: {app.config['MAIL_PORT']}
- MAIL_USE_TLS: {app.config['MAIL_USE_TLS']}
- From: {app.config['MAIL_FROM'] or app.config['MAIL_USERNAME']}
- To: {to_email}

Sent at: {format_date_for_user(datetime.now().date(), user)} {datetime.now().strftime('%H:%M:%S')}

This is an automated test email from your Subscription Tracker.
        """

        # Create HTML version
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background-color: #28a745; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .info-box {{ background-color: #f8f9fa; border-left: 4px solid #28a745; margin: 10px 0; padding: 15px; }}
                .footer {{ background-color: #f8f9fa; padding: 15px; text-align: center; color: #666; }}
                .success {{ color: #28a745; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🧪 Test Email Successful!</h1>
            </div>
            
            <div class="content">
                <p>Hello <strong>{user.username}</strong>,</p>
                <p class="success">✅ Your email configuration is working correctly!</p>
                <p>This is a test email from your Subscription Tracker application to verify that email notifications are properly configured.</p>
                
                <div class="info-box">
                    <h3>📋 Configuration Details:</h3>
                    <ul>
                        <li><strong>Mail Server:</strong> {app.config['MAIL_SERVER']}</li>
                        <li><strong>Port:</strong> {app.config['MAIL_PORT']}</li>
                        <li><strong>TLS Enabled:</strong> {app.config['MAIL_USE_TLS']}</li>
                        <li><strong>From Address:</strong> {app.config['MAIL_FROM'] or app.config['MAIL_USERNAME']}</li>
                        <li><strong>To Address:</strong> {to_email}</li>
                        <li><strong>Sent At:</strong> {format_date_for_user(datetime.now().date(), user)} {datetime.now().strftime('%H:%M:%S')}</li>
                    </ul>
                </div>
                
                <p>Now you can be confident that your subscription expiry notifications will be delivered successfully!</p>
            </div>
            
            <div class="footer">
                <p>This is an automated test email from your Subscription Tracker.</p>
            </div>
        </body>
        </html>
        """

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
                print("📨 Sending test email...")
                server.send_message(msg)
                
                print(f"✅ Test email sent successfully to {user.username}")
                return {
                    'success': True,
                    'message': f'Test email sent successfully to {to_email}!'
                }
                
        except smtplib.SMTPAuthenticationError as e:
            error_msg = f"SMTP Authentication failed: {e}. Check MAIL_USERNAME and MAIL_PASSWORD."
            print(f"❌ {error_msg}")
            return {
                'success': False,
                'message': error_msg
            }
        except smtplib.SMTPConnectError as e:
            error_msg = f"Failed to connect to mail server: {e}. Check MAIL_SERVER and MAIL_PORT."
            print(f"❌ {error_msg}")
            return {
                'success': False,
                'message': error_msg
            }
        except smtplib.SMTPRecipientsRefused as e:
            error_msg = f"Recipient refused: {e}. Check email address."
            print(f"❌ {error_msg}")
            return {
                'success': False,
                'message': error_msg
            }
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            print(f"❌ {error_msg}")
            return {
                'success': False,
                'message': error_msg
            }
