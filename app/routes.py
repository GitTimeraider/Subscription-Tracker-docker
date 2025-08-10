from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User, Subscription, UserSettings, PaymentMethod
from app.forms import (LoginForm, RegistrationForm, SubscriptionForm, UserSettingsForm, 
                      NotificationSettingsForm, EmailSettingsForm, PaymentMethodForm)
from app.currency import currency_converter
from datetime import datetime, timedelta
import os

main = Blueprint('main', __name__)

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
            return redirect(next_page) if next_page else redirect(url_for('main.dashboard'))
        flash('Invalid username or password', 'error')
    return render_template('login.html', form=form)

@main.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        
        # Create default user settings
        settings = UserSettings(user_id=user.id)
        db.session.add(settings)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('main.login'))
    return render_template('register.html', form=form)

@main.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.login'))

@main.route('/dashboard')
@login_required
def dashboard():
    # Get filter parameters
    category_filter = request.args.get('category', 'all')
    status_filter = request.args.get('status', 'all')
    
    # Base query
    query = Subscription.query.filter_by(user_id=current_user.id)
    
    # Apply filters
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
    
    subscriptions = query.order_by(Subscription.end_date.asc()).all()
    
    # Get user settings for currency conversion
    user_settings = current_user.settings or UserSettings()
    user_currency = user_settings.currency
    
    # Set up currency converter with user's API key if available
    if user_settings.fixer_api_key:
        currency_converter.set_api_key(user_settings.fixer_api_key)
    
    # Calculate totals in user's preferred currency
    total_monthly = sum(sub.get_monthly_cost_in_currency(user_currency) for sub in subscriptions if sub.is_active)
    total_yearly = sum(sub.get_yearly_cost_in_currency(user_currency) for sub in subscriptions if sub.is_active)
    
    # Get categories for filter
    categories = db.session.query(Subscription.category.distinct()).filter_by(user_id=current_user.id).all()
    categories = [cat[0] for cat in categories if cat[0]]
    
    # Check for expiring subscriptions
    expiring_soon = [sub for sub in subscriptions 
                    if sub.is_expiring_soon(user_settings.notification_days)]
    
    # Get currency symbol for display
    currency_symbol = currency_converter.get_currency_symbol(user_currency)
    
    return render_template('dashboard.html', 
                         subscriptions=subscriptions,
                         total_monthly=total_monthly,
                         total_yearly=total_yearly,
                         categories=categories,
                         current_category=category_filter,
                         current_status=status_filter,
                         expiring_soon=expiring_soon,
                         user_currency=user_currency,
                         currency_symbol=currency_symbol)

@main.route('/add_subscription', methods=['GET', 'POST'])
@login_required
def add_subscription():
    form = SubscriptionForm()
    if form.validate_on_submit():
        payment_method_id = form.payment_method_id.data if form.payment_method_id.data != 0 else None
        
        subscription = Subscription(
            name=form.name.data,
            company=form.company.data,
            category=form.category.data,
            cost=form.cost.data,
            currency=form.currency.data,
            billing_cycle=form.billing_cycle.data,
            custom_days=form.custom_days.data if form.billing_cycle.data == 'custom' else None,
            payment_method_id=payment_method_id,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            notes=form.notes.data,
            user_id=current_user.id
        )
        db.session.add(subscription)
        db.session.commit()
        flash('Subscription added successfully!', 'success')
        return redirect(url_for('main.dashboard'))
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
        payment_method_id = form.payment_method_id.data if form.payment_method_id.data != 0 else None
        
        subscription.name = form.name.data
        subscription.company = form.company.data
        subscription.category = form.category.data
        subscription.cost = form.cost.data
        subscription.currency = form.currency.data
        subscription.billing_cycle = form.billing_cycle.data
        subscription.custom_days = form.custom_days.data if form.billing_cycle.data == 'custom' else None
        subscription.payment_method_id = payment_method_id
        subscription.start_date = form.start_date.data
        subscription.end_date = form.end_date.data
        subscription.notes = form.notes.data
        db.session.commit()
        flash('Subscription updated successfully!', 'success')
        return redirect(url_for('main.dashboard'))
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
        # Check current password if trying to change password or email
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
        settings.notification_days = form.notification_days.data
        settings.currency = form.currency.data
        settings.fixer_api_key = form.fixer_api_key.data
        settings.timezone = form.timezone.data
        
        db.session.commit()
        flash('Notification settings updated successfully!', 'success')
        return redirect(url_for('main.notification_settings'))
    
    return render_template('notification_settings.html', form=form)

@main.route('/email_settings', methods=['GET', 'POST'])
@login_required
def email_settings():
    # Only admin can access email settings (for security)
    if current_user.username != 'admin':
        flash('Access denied', 'error')
        return redirect(url_for('main.dashboard'))
    
    form = EmailSettingsForm()
    
    # Load current values from environment/config
    if request.method == 'GET':
        form.mail_server.data = os.environ.get('MAIL_SERVER', '')
        form.mail_port.data = int(os.environ.get('MAIL_PORT', 587))
        form.mail_use_tls.data = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', '1', 'on']
        form.mail_username.data = os.environ.get('MAIL_USERNAME', '')
        form.mail_from.data = os.environ.get('MAIL_FROM', '')
    
    if form.validate_on_submit():
        # In a real application, you'd want to store these securely
        # For now, we'll just show a message about updating environment variables
        flash('Email settings would be updated. In production, update your environment variables.', 'info')
        return redirect(url_for('main.email_settings'))
    
    return render_template('email_settings.html', form=form)

@main.route('/analytics')
@login_required
def analytics():
    subscriptions = Subscription.query.filter_by(user_id=current_user.id).all()
    
    # Get user settings for currency conversion
    user_settings = current_user.settings or UserSettings()
    user_currency = user_settings.currency
    
    # Set up currency converter with user's API key if available
    if user_settings.fixer_api_key:
        currency_converter.set_api_key(user_settings.fixer_api_key)
    
    # Calculate analytics
    active_subs = [s for s in subscriptions if s.is_active]
    total_monthly = sum(sub.get_monthly_cost_in_currency(user_currency) for sub in active_subs)
    total_yearly = sum(sub.get_yearly_cost_in_currency(user_currency) for sub in active_subs)
    
    # Category breakdown
    category_costs = {}
    for sub in active_subs:
        category = sub.category or 'other'
        if category not in category_costs:
            category_costs[category] = 0
        category_costs[category] += sub.get_monthly_cost_in_currency(user_currency)
    
    # Billing cycle breakdown
    cycle_costs = {}
    for sub in active_subs:
        cycle = sub.billing_cycle
        if cycle not in cycle_costs:
            cycle_costs[cycle] = 0
        cycle_costs[cycle] += sub.get_monthly_cost_in_currency(user_currency)
    
    # Upcoming renewals
    upcoming = []
    for sub in subscriptions:
        if sub.end_date and sub.is_active:
            days_left = sub.days_until_expiry()
            if days_left is not None and days_left <= 30:
                upcoming.append({
                    'subscription': sub,
                    'days_left': days_left
                })
    
    upcoming.sort(key=lambda x: x['days_left'])
    
    # Get currency symbol for display
    currency_symbol = currency_converter.get_currency_symbol(user_currency)
    
    return render_template('analytics.html',
                         total_monthly=total_monthly,
                         total_yearly=total_yearly,
                         category_costs=category_costs,
                         cycle_costs=cycle_costs,
                         upcoming=upcoming,
                         active_count=len(active_subs),
                         total_count=len(subscriptions),
                         user_currency=user_currency,
                         currency_symbol=currency_symbol)

@main.route('/api/subscription_data')
@login_required
def api_subscription_data():
    """API endpoint for chart data"""
    subscriptions = Subscription.query.filter_by(user_id=current_user.id, is_active=True).all()
    
    # Get user settings for currency conversion
    user_settings = current_user.settings or UserSettings()
    user_currency = user_settings.currency
    
    # Set up currency converter with user's API key if available
    if user_settings.fixer_api_key:
        currency_converter.set_api_key(user_settings.fixer_api_key)
    
    category_data = {}
    for sub in subscriptions:
        category = sub.category or 'other'
        if category not in category_data:
            category_data[category] = 0
        category_data[category] += sub.get_monthly_cost_in_currency(user_currency)
    
    return jsonify(category_data)

@main.route('/payment_methods')
@login_required
def payment_methods():
    """List all payment methods for the current user"""
    payment_methods = PaymentMethod.query.filter_by(user_id=current_user.id).all()
    return render_template('payment_methods.html', payment_methods=payment_methods)

@main.route('/add_payment_method', methods=['GET', 'POST'])
@login_required
def add_payment_method():
    """Add a new payment method"""
    form = PaymentMethodForm()
    if form.validate_on_submit():
        payment_method = PaymentMethod(
            name=form.name.data,
            payment_type=form.payment_type.data,
            last_four=form.last_four.data,
            notes=form.notes.data,
            user_id=current_user.id
        )
        db.session.add(payment_method)
        db.session.commit()
        flash('Payment method added successfully!', 'success')
        return redirect(url_for('main.payment_methods'))
    return render_template('add_payment_method.html', form=form)

@main.route('/edit_payment_method/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_payment_method(id):
    """Edit an existing payment method"""
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
    """Delete a payment method"""
    payment_method = PaymentMethod.query.get_or_404(id)
    if payment_method.user_id != current_user.id:
        flash('Unauthorized access', 'error')
        return redirect(url_for('main.payment_methods'))

    # Check if any subscriptions are using this payment method
    subscriptions_using = Subscription.query.filter_by(payment_method_id=id).all()
    if subscriptions_using:
        flash(f'Cannot delete payment method. It is used by {len(subscriptions_using)} subscription(s).', 'error')
        return redirect(url_for('main.payment_methods'))

    db.session.delete(payment_method)
    db.session.commit()
    flash('Payment method deleted successfully!', 'success')
    return redirect(url_for('main.payment_methods'))
