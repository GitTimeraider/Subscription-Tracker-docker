from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, send_from_directory
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User, Subscription, UserSettings, PaymentMethod, ExchangeRate
from app.forms import (LoginForm, RegistrationForm, SubscriptionForm, UserSettingsForm, 
                      NotificationSettingsForm, GeneralSettingsForm, EmailSettingsForm, PaymentMethodForm)
from app.currency import currency_converter
from datetime import datetime, timedelta, date
import os

main = Blueprint('main', __name__)

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
    subscriptions = query.order_by(Subscription.end_date.asc()).all()

    user_settings = current_user.settings or UserSettings()
    display_currency = request.args.get('currency', user_settings.currency)
    # Apply preferred provider priority early (before any rate fetch inside subscription helpers)
    if user_settings.preferred_rate_provider:
        defaults = ['exchangerate_host','frankfurter','ecb']
        priority = [user_settings.preferred_rate_provider] + [p for p in defaults if p != user_settings.preferred_rate_provider]
        os.environ['CURRENCY_PROVIDER_PRIORITY'] = ','.join(priority)
    total_monthly = sum(sub.get_monthly_cost_in_currency(display_currency) for sub in subscriptions if sub.is_active)
    total_yearly = sum(sub.get_yearly_cost_in_currency(display_currency) for sub in subscriptions if sub.is_active)
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
        subscription.custom_period_type = form.custom_period_type.data if form.billing_cycle.data == 'custom' else None
        subscription.custom_period_value = form.custom_period_value.data if form.billing_cycle.data == 'custom' else None
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
        db.session.commit()
        flash('Notification settings updated successfully!', 'success')
        return redirect(url_for('main.notification_settings'))
    return render_template('notification_settings.html', form=form)

@main.route('/general_settings', methods=['GET', 'POST'])
@login_required
def general_settings():
    settings = current_user.settings or UserSettings(user_id=current_user.id)
    form = GeneralSettingsForm(obj=settings)
    # Apply user preferred provider before fetching
    if settings.preferred_rate_provider:
        defaults = ['exchangerate_host','frankfurter','ecb']
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
        db.session.commit()
        # If provider changed, clear today's cache and force fetch
        if settings.preferred_rate_provider and settings.preferred_rate_provider != original_provider_pref:
            currency_converter.clear_today_cache('EUR')
            defaults = ['exchangerate_host','frankfurter','ecb']
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

@main.route('/email_settings', methods=['GET', 'POST'])
@login_required
def email_settings():
    settings = current_user.settings or UserSettings(user_id=current_user.id)
    form = EmailSettingsForm(obj=settings)
    if form.validate_on_submit():
        if not current_user.settings:
            settings = UserSettings(user_id=current_user.id)
            db.session.add(settings)
        else:
            settings = current_user.settings
        settings.mail_server = form.mail_server.data
        settings.mail_port = form.mail_port.data
        settings.mail_use_tls = form.mail_use_tls.data
        settings.mail_username = form.mail_username.data
        settings.mail_password = form.mail_password.data
        settings.mail_from = form.mail_from.data
        db.session.commit()
        flash('Email settings updated successfully!', 'success')
        return redirect(url_for('main.email_settings'))
    return render_template('email_settings.html', form=form)

@main.route('/analytics')
@login_required
def analytics():
    subscriptions = Subscription.query.filter_by(user_id=current_user.id).all()
    user_settings = current_user.settings or UserSettings()
    display_currency = request.args.get('currency', user_settings.currency)
    if user_settings.preferred_rate_provider:
        defaults = ['exchangerate_host','frankfurter','ecb']
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
                upcoming.append({'subscription': sub,'days_left': days_left})
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
        defaults = ['exchangerate_host','frankfurter','ecb']
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
        defaults = ['exchangerate_host','frankfurter','ecb']
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
