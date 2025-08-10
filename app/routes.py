from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User, Subscription
from app.forms import LoginForm, SubscriptionForm
from datetime import datetime

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
            return redirect(url_for('main.dashboard'))
        flash('Invalid username or password')
    return render_template('login.html', form=form)

@main.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.login'))

@main.route('/dashboard')
@login_required
def dashboard():
    subscriptions = Subscription.query.filter_by(user_id=current_user.id).all()
    total_monthly = sum(sub.get_monthly_cost() for sub in subscriptions)
    return render_template('dashboard.html', 
                         subscriptions=subscriptions,
                         total_monthly=total_monthly)

@main.route('/add_subscription', methods=['GET', 'POST'])
@login_required
def add_subscription():
    form = SubscriptionForm()
    if form.validate_on_submit():
        subscription = Subscription(
            name=form.name.data,
            company=form.company.data,
            cost=form.cost.data,
            billing_cycle=form.billing_cycle.data,
            custom_days=form.custom_days.data if form.billing_cycle.data == 'custom' else None,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            user_id=current_user.id
        )
        db.session.add(subscription)
        db.session.commit()
        flash('Subscription added successfully!')
        return redirect(url_for('main.dashboard'))
    return render_template('add_subscription.html', form=form)

@main.route('/edit_subscription/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_subscription(id):
    subscription = Subscription.query.get_or_404(id)
    if subscription.user_id != current_user.id:
        flash('Unauthorized')
        return redirect(url_for('main.dashboard'))

    form = SubscriptionForm(obj=subscription)
    if form.validate_on_submit():
        subscription.name = form.name.data
        subscription.company = form.company.data
        subscription.cost = form.cost.data
        subscription.billing_cycle = form.billing_cycle.data
        subscription.custom_days = form.custom_days.data if form.billing_cycle.data == 'custom' else None
        subscription.start_date = form.start_date.data
        subscription.end_date = form.end_date.data
        db.session.commit()
        flash('Subscription updated successfully!')
        return redirect(url_for('main.dashboard'))
    return render_template('edit_subscription.html', form=form, subscription=subscription)

@main.route('/delete_subscription/<int:id>')
@login_required
def delete_subscription(id):
    subscription = Subscription.query.get_or_404(id)
    if subscription.user_id != current_user.id:
        flash('Unauthorized')
        return redirect(url_for('main.dashboard'))

    db.session.delete(subscription)
    db.session.commit()
    flash('Subscription deleted successfully!')
    return redirect(url_for('main.dashboard'))
