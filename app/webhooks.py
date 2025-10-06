"""
Webhook notification system for Subscription Tracker

Supports multiple webhook types:
- Discord
- Slack
- Microsoft Teams
- Gotify
- Generic webhooks

This module handles sending notifications about expiring subscriptions
and testing webhook configurations.
"""

import requests
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from flask import current_app

# Set up logging
logger = logging.getLogger(__name__)


class WebhookSender:
    """Base class for webhook senders"""
    
    def __init__(self, webhook):
        self.webhook = webhook
        self.timeout = 30  # seconds
    
    def send(self, message: str, title: str = None, color: str = None) -> Dict[str, Any]:
        """
        Send a webhook message
        
        Args:
            message: The message content
            title: Optional title/subject
            color: Optional color (hex code or name)
        
        Returns:
            Dict with 'success' (bool) and 'message' (str) keys
        """
        try:
            payload = self.prepare_payload(message, title, color)
            headers = self.webhook.get_auth_headers()
            
            logger.info(f"Sending {self.webhook.webhook_type} webhook to {self.webhook.name}")
            
            response = requests.post(
                self.webhook.url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            
            # Update last_used timestamp
            self.webhook.last_used = datetime.now(timezone.utc)
            from app import db
            db.session.commit()
            
            logger.info(f"Successfully sent {self.webhook.webhook_type} webhook")
            return {
                'success': True,
                'message': f'Webhook sent successfully to {self.webhook.name}',
                'status_code': response.status_code
            }
            
        except requests.exceptions.Timeout:
            error_msg = f'Webhook request to {self.webhook.name} timed out after {self.timeout} seconds'
            logger.error(error_msg)
            return {'success': False, 'message': error_msg}
            
        except requests.exceptions.ConnectionError:
            error_msg = f'Failed to connect to webhook {self.webhook.name}'
            logger.error(error_msg)
            return {'success': False, 'message': error_msg}
            
        except requests.exceptions.HTTPError as e:
            error_msg = f'Webhook {self.webhook.name} returned HTTP error: {e.response.status_code}'
            logger.error(f"{error_msg} - Response: {e.response.text[:200]}")
            return {'success': False, 'message': error_msg}
            
        except Exception as e:
            error_msg = f'Unexpected error sending webhook to {self.webhook.name}: {str(e)}'
            logger.error(error_msg, exc_info=True)
            return {'success': False, 'message': error_msg}
    
    def prepare_payload(self, message: str, title: str = None, color: str = None) -> Dict[str, Any]:
        """Prepare the webhook payload - override in subclasses"""
        return {"text": message}


class DiscordWebhookSender(WebhookSender):
    """Discord webhook sender"""
    
    def prepare_payload(self, message: str, title: str = None, color: str = None) -> Dict[str, Any]:
        # Convert color name to Discord color integer
        color_map = {
            'red': 0xFF0000,
            'orange': 0xFF8C00,
            'yellow': 0xFFFF00,
            'green': 0x00FF00,
            'blue': 0x0000FF,
            'purple': 0x800080,
            'pink': 0xFFC0CB
        }
        
        embed = {
            "description": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "footer": {
                "text": "Subscription Tracker"
            }
        }
        
        if title:
            embed["title"] = title
        
        if color:
            if isinstance(color, str):
                if color.startswith('#'):
                    # Convert hex color to integer
                    embed["color"] = int(color[1:], 16)
                elif color.lower() in color_map:
                    embed["color"] = color_map[color.lower()]
            elif isinstance(color, int):
                embed["color"] = color
        else:
            embed["color"] = 0x7289DA  # Discord blurple
        
        return {
            "embeds": [embed]
        }


class SlackWebhookSender(WebhookSender):
    """Slack webhook sender"""
    
    def prepare_payload(self, message: str, title: str = None, color: str = None) -> Dict[str, Any]:
        # Slack color mapping
        color_map = {
            'red': 'danger',
            'orange': 'warning',
            'yellow': 'warning',
            'green': 'good',
        }
        
        attachment = {
            "text": message,
            "ts": int(datetime.now(timezone.utc).timestamp()),
            "footer": "Subscription Tracker"
        }
        
        if title:
            attachment["title"] = title
        
        if color:
            if color.lower() in color_map:
                attachment["color"] = color_map[color.lower()]
            elif color in ['good', 'warning', 'danger']:
                attachment["color"] = color
            else:
                attachment["color"] = color  # Custom hex color
        
        return {
            "attachments": [attachment]
        }


class TeamsWebhookSender(WebhookSender):
    """Microsoft Teams webhook sender"""
    
    def prepare_payload(self, message: str, title: str = None, color: str = None) -> Dict[str, Any]:
        # Teams theme color mapping
        color_map = {
            'red': 'FF0000',
            'orange': 'FF8C00',
            'yellow': 'FFD700',
            'green': '00FF00',
            'blue': '0078D4',  # Microsoft blue
            'purple': '800080'
        }
        
        card = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "summary": title or "Subscription Tracker Notification",
            "text": message,
            "potentialAction": []
        }
        
        if title:
            card["title"] = title
        
        if color:
            theme_color = color
            if color.lower() in color_map:
                theme_color = color_map[color.lower()]
            elif color.startswith('#'):
                theme_color = color[1:]  # Remove # for Teams
            card["themeColor"] = theme_color
        
        return card


class GotifyWebhookSender(WebhookSender):
    """Gotify webhook sender"""
    
    def prepare_payload(self, message: str, title: str = None, color: str = None) -> Dict[str, Any]:
        # Gotify priority mapping
        priority_map = {
            'red': 8,      # High priority
            'orange': 6,   # Medium-high priority
            'yellow': 4,   # Medium priority
            'green': 2,    # Low priority
            'blue': 2,     # Low priority
        }
        
        payload = {
            "message": message,
            "priority": priority_map.get(color, 4) if color else 4
        }
        
        if title:
            payload["title"] = title
        else:
            payload["title"] = "Subscription Tracker"
        
        return payload


class GenericWebhookSender(WebhookSender):
    """Generic webhook sender for custom webhook formats"""
    
    def prepare_payload(self, message: str, title: str = None, color: str = None) -> Dict[str, Any]:
        payload = {
            "text": message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        if title:
            payload["title"] = title
        
        if color:
            payload["color"] = color
        
        return payload


def get_webhook_sender(webhook) -> WebhookSender:
    """Factory function to get the appropriate webhook sender"""
    sender_map = {
        'discord': DiscordWebhookSender,
        'slack': SlackWebhookSender,
        'teams': TeamsWebhookSender,
        'gotify': GotifyWebhookSender,
        'generic': GenericWebhookSender
    }
    
    sender_class = sender_map.get(webhook.webhook_type, GenericWebhookSender)
    return sender_class(webhook)


def send_test_webhook(app, webhook, user) -> Dict[str, Any]:
    """
    Send a test webhook message
    
    Args:
        app: Flask application instance
        webhook: Webhook model instance
        user: User model instance
    
    Returns:
        Dict with 'success' (bool) and 'message' (str) keys
    """
    if not webhook.is_active:
        return {
            'success': False,
            'message': f'Webhook "{webhook.name}" is disabled'
        }
    
    with app.app_context():
        try:
            sender = get_webhook_sender(webhook)
            
            test_message = (
                f"🧪 **Test Webhook from Subscription Tracker**\n\n"
                f"Hello {user.username}!\n\n"
                f"This is a test message to verify your {webhook.webhook_type} webhook configuration.\n\n"
                f"**Webhook Details:**\n"
                f"• Name: {webhook.name}\n"
                f"• Type: {webhook.webhook_type.title()}\n"
                f"• Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"If you received this message, your webhook is working correctly! 🎉"
            )
            
            result = sender.send(
                message=test_message,
                title="🧪 Webhook Test - Subscription Tracker",
                color="blue"
            )
            
            logger.info(f"Test webhook sent to {webhook.name} for user {user.username}: {result}")
            return result
            
        except Exception as e:
            error_msg = f'Failed to send test webhook: {str(e)}'
            logger.error(error_msg, exc_info=True)
            return {'success': False, 'message': error_msg}


def send_all_webhook_notifications(app, user, expiring_subscriptions) -> int:
    """
    Send webhook notifications for expiring subscriptions
    
    Args:
        app: Flask application instance
        user: User model instance
        expiring_subscriptions: List of expiring subscriptions
    
    Returns:
        int: Number of webhooks sent successfully
    """
    if not expiring_subscriptions:
        return 0
    
    with app.app_context():
        try:
            from app.models import Webhook
            
            # Get active webhooks for the user
            webhooks = Webhook.query.filter_by(user_id=user.id, is_active=True).all()
            
            if not webhooks:
                logger.info(f"No active webhooks configured for user {user.username}")
                return 0
            
            successful_sends = 0
            
            # Prepare the notification message
            message_parts = [
                f"🔔 **Subscription Expiry Notification**",
                f"",
                f"Hello {user.username}!",
                f"",
                f"You have {len(expiring_subscriptions)} subscription(s) expiring soon:",
                f""
            ]
            
            total_cost = 0
            user_currency = user.settings.currency if user.settings else 'EUR'
            
            for sub in expiring_subscriptions:
                days_left = sub.days_until_expiry()
                
                # Convert cost to user's preferred currency
                cost_display = sub.get_cost_in_currency(user_currency)
                
                if days_left is not None:
                    if days_left == 0:
                        status = "⚠️ **EXPIRES TODAY**"
                    elif days_left == 1:
                        status = "⚠️ **Expires tomorrow**"
                    else:
                        status = f"📅 Expires in {days_left} days"
                else:
                    status = "📅 Check expiry date"
                
                message_parts.append(
                    f"• **{sub.name}** by {sub.company} - "
                    f"{cost_display:.2f} {user_currency}/{sub.billing_cycle} - {status}"
                )
                
                total_cost += cost_display
            
            if total_cost > 0:
                message_parts.extend([
                    f"",
                    f"💰 **Total expiring cost:** {total_cost:.2f} {user_currency}",
                ])
            
            message_parts.extend([
                f"",
                f"Don't forget to review and renew your subscriptions as needed!",
                f"",
                f"Manage your subscriptions: [Dashboard Link]"
            ])
            
            notification_message = "\n".join(message_parts)
            
            # Send to all active webhooks
            for webhook in webhooks:
                try:
                    sender = get_webhook_sender(webhook)
                    
                    # Determine color based on urgency
                    urgency_color = "red"  # Default to urgent
                    min_days = min([sub.days_until_expiry() or 0 for sub in expiring_subscriptions])
                    
                    if min_days == 0:
                        urgency_color = "red"      # Expires today
                    elif min_days <= 1:
                        urgency_color = "orange"   # Expires very soon
                    elif min_days <= 3:
                        urgency_color = "yellow"   # Expires soon
                    else:
                        urgency_color = "blue"     # Advance notice
                    
                    result = sender.send(
                        message=notification_message,
                        title=f"🔔 {len(expiring_subscriptions)} Subscription(s) Expiring Soon",
                        color=urgency_color
                    )
                    
                    if result['success']:
                        successful_sends += 1
                        logger.info(f"Notification webhook sent to {webhook.name} for user {user.username}")
                    else:
                        logger.error(f"Failed to send notification webhook to {webhook.name}: {result['message']}")
                        
                except Exception as e:
                    logger.error(f"Error sending webhook to {webhook.name}: {str(e)}", exc_info=True)
            
            logger.info(f"Sent {successful_sends}/{len(webhooks)} webhook notifications for user {user.username}")
            return successful_sends
            
        except Exception as e:
            logger.error(f"Failed to send webhook notifications for user {user.username}: {str(e)}", exc_info=True)
            return 0


def validate_webhook_url(webhook_type: str, url: str) -> Dict[str, Any]:
    """
    Validate a webhook URL format for a specific webhook type
    
    Args:
        webhook_type: Type of webhook (discord, slack, teams, gotify, generic)  
        url: The webhook URL to validate
    
    Returns:
        Dict with 'valid' (bool) and 'message' (str) keys
    """
    if not url or not url.strip():
        return {'valid': False, 'message': 'URL cannot be empty'}
    
    url = url.strip()
    
    # Basic URL validation
    if not url.startswith(('http://', 'https://')):
        return {'valid': False, 'message': 'URL must start with http:// or https://'}
    
    # Type-specific validation
    if webhook_type == 'discord':
        if 'discord.com' not in url or '/webhooks/' not in url:
            return {'valid': False, 'message': 'Discord webhook URL must contain discord.com and /webhooks/'}
    
    elif webhook_type == 'slack':
        if 'hooks.slack.com' not in url:
            return {'valid': False, 'message': 'Slack webhook URL must contain hooks.slack.com'}
    
    elif webhook_type == 'teams':
        if 'outlook.office.com' not in url and 'outlook.office365.com' not in url:
            return {'valid': False, 'message': 'Teams webhook URL must be an Office 365 connector URL'}
    
    # URL appears valid
    return {'valid': True, 'message': 'URL format appears valid'}


# For backwards compatibility and ease of import
__all__ = [
    'send_test_webhook',
    'send_all_webhook_notifications', 
    'validate_webhook_url',
    'get_webhook_sender',
    'WebhookSender',
    'DiscordWebhookSender',
    'SlackWebhookSender', 
    'TeamsWebhookSender',
    'GotifyWebhookSender',
    'GenericWebhookSender'
]