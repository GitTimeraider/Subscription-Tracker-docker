from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, send_from_directory, current_app
from urllib.parse import urlparse
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User, Subscription, UserSettings, PaymentMethod, ExchangeRate, Webhook
from app.forms import (LoginForm, SubscriptionForm, UserSettingsForm, 
                      NotificationSettingsForm, GeneralSettingsForm, PaymentMethodForm,
                      AdminUserForm, AdminEditUserForm, WebhookForm)
from app.currency import currency_converter
from datetime import datetime, timedelta, date
import os

main = Blueprint('main', __name__)

@main.route('/health')
def health_check():
    """Health check endpoint for monitoring"""
    try:
        # Check database connectivity
        db.session.execute('SELECT 1')
        
        # Check if currency converter is working
        from app.currency import currency_converter
        rates_available = bool(currency_converter._get_fallback_rates('EUR'))
        
        return jsonify({
            'status': 'healthy',
            'database': 'ok',
            'currency_rates': 'ok' if rates_available else 'degraded',
            'timestamp': datetime.now().isoformat()
        }), 200
    except Exception as e:
        current_app.logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': 'Health check failed',
            'timestamp': datetime.now().isoformat()
        }), 500

@main.route('/favicon.ico')
def favicon():
    """Serve favicon directly"""
    return send_from_directory(os.path.join(main.root_path, '..', 'static', 'assets', 'img'),
                               'icon_main.ico', mimetype='image/x-icon')

@main.route('/', methods=['GET', 'POST'])
@main.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            if next_page:
                # Remove backslashes and validate that next_page is a relative URL
                next_page_clean = next_page.replace('\\', '')
                parsed = urlparse(next_page_clean)
                if not parsed.netloc and not parsed.scheme:
                    return redirect(next_page_clean)
            return redirect(url_for('main.dashboard'))
        flash('Invalid username or password', 'error')
    return render_template('login.html', form=form)

@main.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.login'))

@main.route('/sync-theme', methods=['POST'])
@login_required
def sync_theme():
    """Sync theme preferences from localStorage to user settings"""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    theme_mode = data.get('theme', 'light')
    accent_color = data.get('accentColor', 'purple')
    
    # Validate values
    if theme_mode not in ['light', 'dark']:
        theme_mode = 'light'
    if accent_color not in ['purple', 'blue', 'green', 'red']:
        accent_color = 'purple'
    
    # Update user settings
    if not current_user.settings:
        settings = UserSettings(user_id=current_user.id)
        db.session.add(settings)
        current_user.settings = settings
    
    current_user.settings.theme_mode = theme_mode
    current_user.settings.accent_color = accent_color
    db.session.commit()
    
    return jsonify({'success': True})

@main.route('/dashboard')
@login_required
def dashboard():
    # Get filter parameters
    category_filter = request.args.get('category', 'all')
    status_filter = request.args.get('status', 'all')
    sort_by = request.args.get('sort', 'end_date')  # Default sort by end_date (nearest expiry first)
    sort_order = request.args.get('order', 'asc')  # Default ascending order (nearest first)
    
    query = Subscription.query.filter_by(user_id=current_user.id)
    if category_filter != 'all':
        query = query.filter_by(category=category_filter)
    if status_filter == 'active':
        query = query.filter_by(is_active=True)
    elif status_filter == 'inactive':
        query = query.filter_by(is_active=False)
    elif status_filter == 'expiring':
        user_settings = current_user.settings or UserSettings()
        days_ahead = user_settings.notification_days
        check_date = datetime.now().date() + timedelta(days=days_ahead)
        query = query.filter(
            Subscription.end_date.isnot(None),
            Subscription.end_date <= check_date,
            Subscription.end_date >= datetime.now().date()
        )
    
    # Apply sorting
    if sort_by == 'name':
        if sort_order == 'desc':
            query = query.order_by(Subscription.name.desc())
        else:
            query = query.order_by(Subscription.name.asc())
    elif sort_by == 'company':
        if sort_order == 'desc':
            query = query.order_by(Subscription.company.desc())
        else:
            query = query.order_by(Subscription.company.asc())
    elif sort_by == 'cost':
        if sort_order == 'desc':
            query = query.order_by(Subscription.cost.desc())
        else:
            query = query.order_by(Subscription.cost.asc())
    elif sort_by == 'start_date':
        if sort_order == 'desc':
            query = query.order_by(Subscription.start_date.desc())
        else:
            query = query.order_by(Subscription.start_date.asc())
    elif sort_by == 'end_date':
        if sort_order == 'desc':
            # For descending: furthest dates first, then infinite (NULL) last
            query = query.order_by(Subscription.end_date.desc().nulls_last(), Subscription.name.asc())
        else:
            # For ascending: nearest dates first, then infinite (NULL) last
            query = query.order_by(Subscription.end_date.asc().nulls_last(), Subscription.name.asc())
    elif sort_by == 'category':
        if sort_order == 'desc':
            # Handle nulls: null categories should appear last
            query = query.order_by(Subscription.category.desc(), Subscription.name.asc())
        else:
            query = query.order_by(Subscription.category.asc(), Subscription.name.asc())
    else:
        # Default fallback to name sorting
        query = query.order_by(Subscription.name.asc())
    
    subscriptions = query.all()
    
    # Handle sorting by monthly cost (calculated field)
    if sort_by == 'monthly_cost':
        user_settings = current_user.settings or UserSettings()
        display_currency = request.args.get('currency', user_settings.currency)
        
        # Apply preferred provider priority for currency conversion
        if user_settings.preferred_rate_provider:
            defaults = ['frankfurter','floatrates','erapi_open']
            priority = [user_settings.preferred_rate_provider] + [p for p in defaults if p != user_settings.preferred_rate_provider]
            os.environ['CURRENCY_PROVIDER_PRIORITY'] = ','.join(priority)
        
        try:
            # Sort by monthly cost in display currency
            subscriptions.sort(
                key=lambda x: x.get_monthly_cost_in_currency(display_currency),
                reverse=(sort_order == 'desc')
            )
        except Exception as e:
            current_app.logger.warning(f"Failed to sort by monthly cost: {e}")
            # Fall back to cost sorting if monthly cost calculation fails
            subscriptions.sort(key=lambda x: x.cost, reverse=(sort_order == 'desc'))
    
    # Handle post-processing sorting for end_date to ensure infinite subscriptions are always last
    if sort_by == 'end_date':
        def end_date_sort_key(subscription):
            if subscription.end_date is None:
                # For infinite subscriptions, use a far future date for sorting
                from datetime import date
                return date(9999, 12, 31)
            return subscription.end_date
        
        subscriptions.sort(
            key=end_date_sort_key,
            reverse=(sort_order == 'desc')
        )

    user_settings = current_user.settings or UserSettings()
    display_currency = request.args.get('currency', user_settings.currency)
    
    # Apply preferred provider priority early (before any rate fetch inside subscription helpers)
    if user_settings.preferred_rate_provider:
        defaults = ['frankfurter','floatrates','erapi_open']
        priority = [user_settings.preferred_rate_provider] + [p for p in defaults if p != user_settings.preferred_rate_provider]
        os.environ['CURRENCY_PROVIDER_PRIORITY'] = ','.join(priority)
    
    # Pre-fetch exchange rates once to avoid multiple API calls during cost calculations
    try:
        from flask import g
        if not hasattr(g, '_eur_rates_cache'):
            g._eur_rates_cache = currency_converter.get_exchange_rates('EUR') or {}
    except Exception as e:
        current_app.logger.warning(f"Failed to pre-fetch exchange rates: {e}")
        # Continue without rates - will use fallback
    
    # Calculate totals with better error handling
    try:
        total_monthly = sum(sub.get_monthly_cost_in_currency(display_currency) for sub in subscriptions if sub.is_active)
        total_yearly = sum(sub.get_yearly_cost_in_currency(display_currency) for sub in subscriptions if sub.is_active)
    except Exception as e:
        current_app.logger.error(f"Error calculating costs: {e}")
        total_monthly = 0
        total_yearly = 0
        flash('Exchange rates temporarily unavailable. Costs may not be accurate.', 'warning')
    
    categories = db.session.query(Subscription.category.distinct()).filter_by(user_id=current_user.id).all()
    categories = [cat[0] for cat in categories if cat[0]]
    expiring_soon = [sub for sub in subscriptions if sub.is_expiring_soon(user_settings.notification_days)]
    currency_symbol = currency_converter.get_currency_symbol(display_currency)
    active_provider = currency_converter.last_provider
    
    return render_template('dashboard.html', 
                         subscriptions=subscriptions,
                         total_monthly=total_monthly,
                         total_yearly=total_yearly,
                         categories=categories,
                         current_category=category_filter,
                         current_status=status_filter,
                         current_sort=sort_by,
                         current_order=sort_order,
                         expiring_soon=expiring_soon,
                         user_currency=display_currency,
                         currency_symbol=currency_symbol,
                         rate_provider=active_provider,
                         requested_provider=user_settings.preferred_rate_provider)

@main.route('/add_subscription', methods=['GET', 'POST'])
@login_required
def add_subscription():
    form = SubscriptionForm()
    if form.validate_on_submit():
        try:
            payment_method_id = form.payment_method_id.data if form.payment_method_id.data != 0 else None
            subscription = Subscription(
                name=form.name.data,
                company=form.company.data,
                category=form.category.data,
                cost=form.cost.data,
                currency=form.currency.data,
                billing_cycle=form.billing_cycle.data,
                custom_period_type=form.custom_period_type.data if form.billing_cycle.data == 'custom' else None,
                custom_period_value=form.custom_period_value.data if form.billing_cycle.data == 'custom' else None,
                payment_method_id=payment_method_id,
                start_date=form.start_date.data,
                end_date=form.end_date.data,
                custom_notification_days=form.custom_notification_days.data,
                notes=form.notes.data,
                user_id=current_user.id
            )
            db.session.add(subscription)
            db.session.commit()
            flash('Subscription added successfully!', 'success')
            return redirect(url_for('main.dashboard'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error adding subscription: {e}")
            flash('An error occurred while saving the subscription. Please try again.', 'error')
            return render_template('add_subscription.html', form=form)
    return render_template('add_subscription.html', form=form)

@main.route('/edit_subscription/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_subscription(id):
    subscription = Subscription.query.get_or_404(id)
    if subscription.user_id != current_user.id:
        flash('Unauthorized access', 'error')
        return redirect(url_for('main.dashboard'))
    form = SubscriptionForm(obj=subscription)
    if form.validate_on_submit():
        try:
            payment_method_id = form.payment_method_id.data if form.payment_method_id.data != 0 else None
            subscription.name = form.name.data
            subscription.company = form.company.data
            subscription.category = form.category.data
            subscription.cost = form.cost.data
            subscription.currency = form.currency.data
            subscription.billing_cycle = form.billing_cycle.data
            subscription.custom_period_type = form.custom_period_type.data if form.billing_cycle.data == 'custom' else None
            subscription.custom_period_value = form.custom_period_value.data if form.billing_cycle.data == 'custom' else None
            subscription.payment_method_id = payment_method_id
            subscription.start_date = form.start_date.data
            subscription.end_date = form.end_date.data
            subscription.custom_notification_days = form.custom_notification_days.data
            subscription.notes = form.notes.data
            db.session.commit()
            flash('Subscription updated successfully!', 'success')
            return redirect(url_for('main.dashboard'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating subscription: {e}")
            flash('An error occurred while updating the subscription. Please try again.', 'error')
            return render_template('edit_subscription.html', form=form, subscription=subscription)
    return render_template('edit_subscription.html', form=form, subscription=subscription)

@main.route('/toggle_subscription/<int:id>')
@login_required
def toggle_subscription(id):
    subscription = Subscription.query.get_or_404(id)
    if subscription.user_id != current_user.id:
        flash('Unauthorized access', 'error')
        return redirect(url_for('main.dashboard'))
    subscription.is_active = not subscription.is_active
    db.session.commit()
    status = 'activated' if subscription.is_active else 'deactivated'
    flash(f'Subscription {status} successfully!', 'success')
    return redirect(url_for('main.dashboard'))

@main.route('/delete_subscription/<int:id>')
@login_required
def delete_subscription(id):
    subscription = Subscription.query.get_or_404(id)
    if subscription.user_id != current_user.id:
        flash('Unauthorized access', 'error')
        return redirect(url_for('main.dashboard'))
    db.session.delete(subscription)
    db.session.commit()
    flash('Subscription deleted successfully!', 'success')
    return redirect(url_for('main.dashboard'))

@main.route('/user_settings', methods=['GET', 'POST'])
@login_required
def user_settings():
    form = UserSettingsForm(obj=current_user)
    if form.validate_on_submit():
        if form.new_password.data or form.email.data != current_user.email:
            if not form.current_password.data or not current_user.check_password(form.current_password.data):
                flash('Current password is required and must be correct', 'error')
                return render_template('user_settings.html', form=form)
        current_user.username = form.username.data
        current_user.email = form.email.data
        if form.new_password.data:
            current_user.set_password(form.new_password.data)
            flash('Password updated successfully!', 'success')
        db.session.commit()
        flash('Settings updated successfully!', 'success')
        return redirect(url_for('main.user_settings'))
    return render_template('user_settings.html', form=form)

@main.route('/notification_settings', methods=['GET', 'POST'])
@login_required
def notification_settings():
    settings = current_user.settings or UserSettings(user_id=current_user.id)
    form = NotificationSettingsForm(obj=settings)
    if form.validate_on_submit():
        if not current_user.settings:
            settings = UserSettings(user_id=current_user.id)
            db.session.add(settings)
        else:
            settings = current_user.settings
        settings.email_notifications = form.email_notifications.data
        settings.webhook_notifications = form.webhook_notifications.data
        settings.notification_days = form.notification_days.data
        settings.notification_time = form.notification_time.data
        db.session.commit()
        flash('Notification settings updated successfully!', 'success')
        return redirect(url_for('main.notification_settings'))
    return render_template('notification_settings.html', form=form)

@main.route('/test_email', methods=['POST'])
@login_required
def test_email():
    """Send a test email to verify email configuration"""
    from app.email import send_test_email
    from flask import current_app
    
    # Check if user has email configured
    if not current_user.email:
        flash('Please set your email address in User Settings before testing email notifications.', 'warning')
        return redirect(url_for('main.notification_settings'))
    
    # Send test email
    result = send_test_email(current_app._get_current_object(), current_user)
    
    if result['success']:
        flash(result['message'], 'success')
    else:
        flash(result['message'], 'error')
    
    return redirect(url_for('main.notification_settings'))

@main.route('/add_webhook', methods=['GET', 'POST'])
@login_required
def add_webhook():
    """Add a new webhook configuration"""
    form = WebhookForm()
    if form.validate_on_submit():
        webhook = Webhook(
            name=form.name.data,
            webhook_type=form.webhook_type.data,
            url=form.url.data,
            auth_header=form.auth_header.data if form.auth_header.data else None,
            auth_username=form.auth_username.data if form.auth_username.data else None,
            auth_password=form.auth_password.data if form.auth_password.data else None,
            custom_headers=form.custom_headers.data if form.custom_headers.data else None,
            is_active=form.is_active.data,
            user_id=current_user.id
        )
        db.session.add(webhook)
        db.session.commit()
        flash(f'Webhook "{webhook.name}" added successfully!', 'success')
        return redirect(url_for('main.notification_settings'))
    return render_template('add_webhook.html', form=form)

@main.route('/edit_webhook/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_webhook(id):
    """Edit an existing webhook configuration"""
    webhook = Webhook.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    form = WebhookForm(obj=webhook)
    
    # Don't populate sensitive fields on GET
    if request.method == 'GET':
        form.auth_header.data = ''
        form.auth_password.data = ''
    
    if form.validate_on_submit():
        webhook.name = form.name.data
        webhook.webhook_type = form.webhook_type.data
        webhook.url = form.url.data
        webhook.is_active = form.is_active.data
        webhook.custom_headers = form.custom_headers.data if form.custom_headers.data else None
        
        # Only update auth fields if they're provided
        if form.auth_header.data:
            webhook.auth_header = form.auth_header.data
        if form.auth_username.data:
            webhook.auth_username = form.auth_username.data
        if form.auth_password.data:
            webhook.auth_password = form.auth_password.data
        
        db.session.commit()
        flash(f'Webhook "{webhook.name}" updated successfully!', 'success')
        return redirect(url_for('main.notification_settings'))
    
    return render_template('edit_webhook.html', form=form, webhook=webhook)

@main.route('/delete_webhook/<int:id>', methods=['POST'])
@login_required
def delete_webhook(id):
    """Delete a webhook configuration"""
    webhook = Webhook.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    webhook_name = webhook.name
    db.session.delete(webhook)
    db.session.commit()
    flash(f'Webhook "{webhook_name}" deleted successfully!', 'success')
    return redirect(url_for('main.notification_settings'))

@main.route('/test_webhook/<int:webhook_id>', methods=['POST'])
@login_required
def test_webhook(webhook_id):
    """Send a test webhook to verify configuration"""
    from app.webhooks import send_test_webhook
    from flask import current_app
    
    webhook = Webhook.query.filter_by(id=webhook_id, user_id=current_user.id).first_or_404()
    
    # Send test webhook
    result = send_test_webhook(current_app._get_current_object(), webhook, current_user)
    
    if result['success']:
        flash(result['message'], 'success')
    else:
        flash(result['message'], 'error')
    
    return redirect(url_for('main.notification_settings'))

@main.route('/general_settings', methods=['GET', 'POST'])
@login_required
def general_settings():
    settings = current_user.settings or UserSettings(user_id=current_user.id)
    form = GeneralSettingsForm(obj=settings)
    # Apply user preferred provider before fetching
    if settings.preferred_rate_provider:
        defaults = ['frankfurter','floatrates','erapi_open']
        priority = [settings.preferred_rate_provider] + [p for p in defaults if p != settings.preferred_rate_provider]
        os.environ['CURRENCY_PROVIDER_PRIORITY'] = ','.join(priority)
    # Fetch rates AFTER applying provider preference
    rates = currency_converter.get_exchange_rates('EUR') or {}
    latest_record = ExchangeRate.query.filter_by(base_currency='EUR', provider=currency_converter.last_provider).order_by(ExchangeRate.created_at.desc()).first()
    last_updated = latest_record.created_at if latest_record else None

    original_provider_pref = settings.preferred_rate_provider
    if form.validate_on_submit():
        if not current_user.settings:
            settings = UserSettings(user_id=current_user.id)
            db.session.add(settings)
        else:
            settings = current_user.settings
        settings.currency = form.currency.data
        settings.timezone = form.timezone.data
        settings.preferred_rate_provider = form.preferred_rate_provider.data
        settings.theme_mode = form.theme_mode.data
        settings.accent_color = form.accent_color.data
        settings.date_format = form.date_format.data
        db.session.commit()
        # If provider changed, clear today's cache and force fetch
        if settings.preferred_rate_provider and settings.preferred_rate_provider != original_provider_pref:
            currency_converter.clear_today_cache('EUR')
            defaults = ['frankfurter','floatrates','erapi_open']
            priority = [settings.preferred_rate_provider] + [p for p in defaults if p != settings.preferred_rate_provider]
            os.environ['CURRENCY_PROVIDER_PRIORITY'] = ','.join(priority)
            currency_converter.get_exchange_rates('EUR', force_refresh=True)
            if currency_converter.last_provider != settings.preferred_rate_provider:
                flash(f"Preferred provider '{settings.preferred_rate_provider}' unavailable; using '{currency_converter.last_provider}'.", 'warning')
        flash('General settings updated successfully!', 'success')
        return redirect(url_for('main.general_settings'))
    # If provider set, ensure form reflects it
    if settings.preferred_rate_provider:
        form.preferred_rate_provider.data = settings.preferred_rate_provider
    return render_template('general_settings.html', form=form, rates=rates, last_updated=last_updated, provider=currency_converter.last_provider, currency_converter=currency_converter, requested_provider=settings.preferred_rate_provider)

@main.route('/analytics')
@login_required
def analytics():
    subscriptions = Subscription.query.filter_by(user_id=current_user.id).all()
    user_settings = current_user.settings or UserSettings()
    display_currency = request.args.get('currency', user_settings.currency)
    if user_settings.preferred_rate_provider:
        defaults = ['frankfurter','floatrates','erapi_open']
        priority = [user_settings.preferred_rate_provider] + [p for p in defaults if p != user_settings.preferred_rate_provider]
        os.environ['CURRENCY_PROVIDER_PRIORITY'] = ','.join(priority)
    active_subs = [s for s in subscriptions if s.is_active]
    total_monthly = sum(sub.get_monthly_cost_in_currency(display_currency) for sub in active_subs)
    total_yearly = sum(sub.get_yearly_cost_in_currency(display_currency) for sub in active_subs)
    category_costs = {}
    for sub in active_subs:
        category = sub.category or 'other'
        if category not in category_costs:
            category_costs[category] = 0
        category_costs[category] += sub.get_monthly_cost_in_currency(display_currency)
    cycle_costs = {}
    for sub in active_subs:
        cycle = sub.billing_cycle
        if cycle not in cycle_costs:
            cycle_costs[cycle] = 0
        cycle_costs[cycle] += sub.get_monthly_cost_in_currency(display_currency)
    upcoming = []
    for sub in subscriptions:
        if sub.end_date and sub.is_active:
            days_left = sub.days_until_expiry()
            if days_left is not None and days_left <= 30:
                upcoming.append({
                    'subscription': sub,
                    'days_left': days_left,
                    'cost_in_display_currency': sub.get_raw_cost_in_currency(display_currency)
                })
    upcoming.sort(key=lambda x: x['days_left'])
    currency_symbol = currency_converter.get_currency_symbol(display_currency)
    active_provider = currency_converter.last_provider
    return render_template('analytics.html',
                         total_monthly=total_monthly,
                         total_yearly=total_yearly,
                         category_costs=category_costs,
                         cycle_costs=cycle_costs,
                         upcoming=upcoming,
                         active_count=len(active_subs),
                         total_count=len(subscriptions),
                         user_currency=display_currency,
                         currency_symbol=currency_symbol,
                         rate_provider=active_provider)

@main.route('/api/subscription_data')
@login_required
def api_subscription_data():
    subscriptions = Subscription.query.filter_by(user_id=current_user.id, is_active=True).all()
    user_settings = current_user.settings or UserSettings()
    display_currency = request.args.get('currency', user_settings.currency)
    if user_settings.preferred_rate_provider:
        defaults = ['frankfurter','floatrates','erapi_open']
        priority = [user_settings.preferred_rate_provider] + [p for p in defaults if p != user_settings.preferred_rate_provider]
        os.environ['CURRENCY_PROVIDER_PRIORITY'] = ','.join(priority)
    category_data = {}
    for sub in subscriptions:
        category = sub.category or 'other'
        if category not in category_data:
            category_data[category] = 0
        category_data[category] += sub.get_monthly_cost_in_currency(display_currency)
    return jsonify(category_data)

@main.route('/debug/refresh_rates')
@login_required
def debug_refresh_rates():
    currency_converter.clear_today_cache('EUR')
    rates = currency_converter.get_exchange_rates('EUR', force_refresh=True) or {}
    sample = {
        'EUR->USD': currency_converter.convert_amount(1, 'EUR', 'USD', rates=rates),
        'USD->EUR': currency_converter.convert_amount(1, 'USD', 'EUR', rates=rates),
        'EUR->GBP': currency_converter.convert_amount(1, 'EUR', 'GBP', rates=rates) if 'GBP' in rates else None,
    }
    return jsonify({'count': len(rates),'usd_rate_raw': rates.get('USD'),'sample_conversions': sample})

@main.route('/refresh_rates', methods=['POST'])
@login_required
def refresh_rates():
    """Force refresh exchange rates and redirect back to general settings."""
    settings = current_user.settings or UserSettings()
    if settings.preferred_rate_provider:
        defaults = ['frankfurter','floatrates','erapi_open']
        priority = [settings.preferred_rate_provider] + [p for p in defaults if p != settings.preferred_rate_provider]
        os.environ['CURRENCY_PROVIDER_PRIORITY'] = ','.join(priority)
    currency_converter.clear_today_cache('EUR')
    rates = currency_converter.get_exchange_rates('EUR', force_refresh=True) or {}
    if settings.preferred_rate_provider and currency_converter.last_provider != settings.preferred_rate_provider:
        flash(f"Preferred provider '{settings.preferred_rate_provider}' unavailable; using '{currency_converter.last_provider}'.", 'warning')
    usd = rates.get('USD')
    gbp = rates.get('GBP')
    flash(f'Exchange rates refreshed. EUR->USD: {usd}, EUR->GBP: {gbp}', 'success')
    return redirect(url_for('main.general_settings'))

@main.route('/payment_methods')
@login_required
def payment_methods():
    payment_methods = PaymentMethod.query.filter_by(user_id=current_user.id).all()
    return render_template('payment_methods.html', payment_methods=payment_methods)

@main.route('/add_payment_method', methods=['GET', 'POST'])
@login_required
def add_payment_method():
    form = PaymentMethodForm()
    if form.validate_on_submit():
        payment_method = PaymentMethod(name=form.name.data,payment_type=form.payment_type.data,last_four=form.last_four.data,notes=form.notes.data,user_id=current_user.id)
        db.session.add(payment_method)
        db.session.commit()
        flash('Payment method added successfully!', 'success')
        return redirect(url_for('main.payment_methods'))
    return render_template('add_payment_method.html', form=form)

@main.route('/edit_payment_method/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_payment_method(id):
    payment_method = PaymentMethod.query.get_or_404(id)
    if payment_method.user_id != current_user.id:
        flash('Unauthorized access', 'error')
        return redirect(url_for('main.payment_methods'))
    form = PaymentMethodForm(obj=payment_method)
    if form.validate_on_submit():
        payment_method.name = form.name.data
        payment_method.payment_type = form.payment_type.data
        payment_method.last_four = form.last_four.data
        payment_method.notes = form.notes.data
        db.session.commit()
        flash('Payment method updated successfully!', 'success')
        return redirect(url_for('main.payment_methods'))
    return render_template('edit_payment_method.html', form=form, payment_method=payment_method)

@main.route('/delete_payment_method/<int:id>')
@login_required
def delete_payment_method(id):
    payment_method = PaymentMethod.query.get_or_404(id)
    if payment_method.user_id != current_user.id:
        flash('Unauthorized access', 'error')
        return redirect(url_for('main.payment_methods'))
    subscriptions_using = Subscription.query.filter_by(payment_method_id=id).all()
    if subscriptions_using:
        flash(f'Cannot delete payment method. It is used by {len(subscriptions_using)} subscription(s).', 'error')
        return redirect(url_for('main.payment_methods'))
    db.session.delete(payment_method)
    db.session.commit()
    flash('Payment method deleted successfully!', 'success')
    return redirect(url_for('main.payment_methods'))

# Admin User Management Routes
@main.route('/admin/users')
@login_required
def admin_users():
    if not current_user.is_admin:
        flash('Administrator access required.', 'error')
        return redirect(url_for('main.dashboard'))
    
    users = User.query.all()
    return render_template('admin_users.html', users=users)

@main.route('/admin/users/add', methods=['GET', 'POST'])
@login_required
def admin_add_user():
    if not current_user.is_admin:
        flash('Administrator access required.', 'error')
        return redirect(url_for('main.dashboard'))
    
    form = AdminUserForm()
    if form.validate_on_submit():
        # Check if username already exists
        existing_user = User.query.filter_by(username=form.username.data).first()
        if existing_user:
            flash('Username already exists. Please choose a different one.', 'error')
            return render_template('admin_add_user.html', form=form)
        
        # Check if email already exists
        existing_email = User.query.filter_by(email=form.email.data).first()
        if existing_email:
            flash('Email already registered. Please choose a different one.', 'error')
            return render_template('admin_add_user.html', form=form)
        
        try:
            user = User(
                username=form.username.data,
                email=form.email.data,
                is_admin=form.is_admin.data
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            
            # Create default user settings
            settings = UserSettings(user_id=user.id)
            db.session.add(settings)
            db.session.commit()
            
            flash(f'User {user.username} created successfully!', 'success')
            return redirect(url_for('main.admin_users'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating user: {e}")
            flash('An error occurred while creating the user. Please try again.', 'error')
    
    return render_template('admin_add_user.html', form=form)

@main.route('/admin/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_user(user_id):
    if not current_user.is_admin:
        flash('Administrator access required.', 'error')
        return redirect(url_for('main.dashboard'))
    
    user = User.query.get_or_404(user_id)
    form = AdminEditUserForm(obj=user)
    
    # Check if this is the last admin for validation
    admin_count = User.query.filter_by(is_admin=True).count()
    is_last_admin = user.is_admin and admin_count <= 1
    
    if form.validate_on_submit():
        # Prevent removing admin role from last admin
        if is_last_admin and not form.is_admin.data:
            flash('Cannot remove admin role from the last admin user.', 'error')
            return render_template('admin_edit_user.html', form=form, user=user, is_last_admin=is_last_admin)
        
        # Check if username already exists (exclude current user)
        existing_user = User.query.filter(User.username == form.username.data, User.id != user_id).first()
        if existing_user:
            flash('Username already exists. Please choose a different one.', 'error')
            return render_template('admin_edit_user.html', form=form, user=user, is_last_admin=is_last_admin)
        
        # Check if email already exists (exclude current user)
        existing_email = User.query.filter(User.email == form.email.data, User.id != user_id).first()
        if existing_email:
            flash('Email already registered. Please choose a different one.', 'error')
            return render_template('admin_edit_user.html', form=form, user=user, is_last_admin=is_last_admin)
        
        try:
            user.username = form.username.data
            user.email = form.email.data
            user.is_admin = form.is_admin.data
            
            if form.new_password.data:
                user.set_password(form.new_password.data)
            
            db.session.commit()
            flash(f'User {user.username} updated successfully!', 'success')
            return redirect(url_for('main.admin_users'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating user: {e}")
            flash('An error occurred while updating the user. Please try again.', 'error')
    
    return render_template('admin_edit_user.html', form=form, user=user, is_last_admin=is_last_admin)

@main.route('/admin/users/delete/<int:user_id>')
@login_required
def admin_delete_user(user_id):
    if not current_user.is_admin:
        flash('Administrator access required.', 'error')
        return redirect(url_for('main.dashboard'))
    
    user = User.query.get_or_404(user_id)
    
    # Prevent deleting themselves
    if user.id == current_user.id:
        flash('You cannot delete your own account while logged in.', 'error')
        return redirect(url_for('main.admin_users'))
    
    # Prevent deleting the last admin
    if user.is_admin:
        admin_count = User.query.filter_by(is_admin=True).count()
        if admin_count <= 1:
            flash('Cannot delete the last admin user.', 'error')
            return redirect(url_for('main.admin_users'))
    
    try:
        # Delete user's settings and subscriptions (cascade should handle this)
        db.session.delete(user)
        db.session.commit()
        flash(f'User {user.username} deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting user: {e}")
        flash('An error occurred while deleting the user. Please try again.', 'error')
    
    return redirect(url_for('main.admin_users'))
