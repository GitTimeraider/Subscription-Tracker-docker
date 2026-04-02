"""
Tests for the daily pre-expiration email reminder logic in app/email.py.

Covers:
- Entering the notification window for the first time
- Consecutive daily reminders while the subscription remains in-window
- Same-day deduplication (no duplicate sends within one day)
- Stopping when the subscription has expired or is out of window
- Robustness: notification_days=None falls back to 7 (avoids TypeError)
- Timezone-aware scheduling (notification sent in the user's local timezone)
"""

import os
import pytest
from datetime import datetime, timedelta, timezone, date
from unittest.mock import patch, MagicMock

os.environ.setdefault("SECRET_KEY", "test-secret-key")
# Use a file-backed SQLite DB so Flask-SQLAlchemy's pool settings are valid in tests
_TEST_DB_PATH = "/tmp/test_daily_reminders.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB_PATH}"

# ---------------------------------------------------------------------------
# Test date constants
# ---------------------------------------------------------------------------

# Anchor date used across tests.  The subscription expires five days after
# this date (i.e. on EXPIRY_DATE below) which places it inside the 7-day
# notification window from DAY1 through DAY3.
DAY1 = datetime(2026, 4, 1, 9, 0, tzinfo=timezone.utc)   # First day in window
DAY1_DUP = datetime(2026, 4, 1, 10, 0, tzinfo=timezone.utc)  # Same day, +1 h
DAY1_FAR = datetime(2026, 4, 1, 13, 0, tzinfo=timezone.utc)  # Same day, outside ±1 h window
DAY2 = datetime(2026, 4, 2, 9, 0, tzinfo=timezone.utc)
DAY3 = datetime(2026, 4, 3, 9, 0, tzinfo=timezone.utc)
DAY5 = datetime(2026, 4, 5, 9, 0, tzinfo=timezone.utc)   # Last day before expiry
DAY_AFTER_EXPIRY = datetime(2026, 4, 7, 9, 0, tzinfo=timezone.utc)  # Expired
DAY_BEFORE_WINDOW = datetime(2026, 3, 28, 9, 0, tzinfo=timezone.utc)  # 9 days before expiry
SUB_END_DATE = date(2026, 4, 6)   # Subscription expiry date (5 days from DAY1)


@pytest.fixture(scope="module")
def app():
    """Create a Flask application configured for testing."""
    import importlib
    import app as app_pkg

    # Force re-import so that the DATABASE_URL env var above takes effect before
    # the config module caches the connection string.
    importlib.reload(importlib.import_module("config"))
    importlib.reload(app_pkg)

    from app import create_app, db as _db

    _app = create_app()
    _app.config["TESTING"] = True
    _app.config["WTF_CSRF_ENABLED"] = False

    with _app.app_context():
        _db.create_all()

    yield _app

    # Cleanup the test database file after the test session
    if os.path.exists(_TEST_DB_PATH):
        os.remove(_TEST_DB_PATH)


@pytest.fixture()
def db(app):
    """Provide a clean database session for each test."""
    from app import db as _db

    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def user_with_sub(app, db):
    """
    Create a test user with email notifications enabled and one active subscription
    that expires in 5 days.  Notification window is 7 days, preferred time 09:00 UTC.
    Returns a dict with 'user', 'settings', and 'subscription' keys.
    """
    from app.models import User, UserSettings, Subscription

    with app.app_context():
        user = User(username="testuser", email="test@example.com")
        user.set_password("testpassword")
        db.session.add(user)
        db.session.commit()

        settings = UserSettings(
            user_id=user.id,
            email_notifications=True,
            webhook_notifications=False,
            notification_days=7,
            notification_time=9,
            timezone="UTC",
            last_notification_sent=None,
        )
        db.session.add(settings)
        db.session.commit()

        # Subscription expiring in 5 days – well inside the 7-day window
        sub = Subscription(
            name="Netflix",
            company="Netflix Inc",
            cost=9.99,
            billing_cycle="monthly",
            start_date=DAY1.date() - timedelta(days=30),
            end_date=SUB_END_DATE,  # expires 2026-04-06
            user_id=user.id,
            is_active=True,
        )
        db.session.add(sub)
        db.session.commit()

        return {"user_id": user.id, "settings_id": settings.id, "sub_id": sub.id}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_fake_datetime(fixed_utc: datetime):
    """Return a fake datetime class whose .now() always returns *fixed_utc*."""

    class _FakeDT:
        @staticmethod
        def now(tz=None):
            if tz is not None:
                return fixed_utc
            return fixed_utc.replace(tzinfo=None)

    return _FakeDT


def _run_check(app, at_utc: datetime, emails_sent: list):
    """
    Invoke check_expiring_subscriptions with a mocked current time of *at_utc*.
    Actual SMTP sending is replaced by a collector that appends to *emails_sent*.
    """
    import app.email as email_mod

    def _capture(app_obj, user, subs):
        emails_sent.append({"user": user.username, "count": len(subs)})
        return True

    fake_dt = _make_fake_datetime(at_utc)
    with patch("app.email.datetime", fake_dt):
        with patch.object(email_mod, "send_expiry_notification", side_effect=_capture):
            email_mod.check_expiring_subscriptions(app)


def _get_last_sent(app):
    """Return the last_notification_sent date stored in the DB for 'testuser'."""
    from app.models import User

    with app.app_context():
        from app import db
        db.session.remove()
        user = User.query.filter_by(username="testuser").first()
        if user and user.settings:
            return user.settings.last_notification_sent
        return None


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestEnteringWindow:
    """The first time a subscription falls inside the notification window an
    email must be sent and the sent-date flag must be recorded."""

    def test_first_notification_is_sent(self, app, user_with_sub):
        emails = []
        _run_check(app, DAY1, emails)

        assert len(emails) == 1
        assert emails[0]["user"] == "testuser"
        assert emails[0]["count"] == 1

    def test_last_notification_sent_is_recorded(self, app, user_with_sub):
        emails = []
        _run_check(app, DAY1, emails)

        assert _get_last_sent(app) == DAY1.date()


class TestDailyConsecutiveReminders:
    """Once inside the window the system must send one email per calendar day."""

    def test_reminder_sent_on_consecutive_days(self, app, user_with_sub):
        emails = []

        # Day 1
        _run_check(app, DAY1, emails)
        # Day 2
        _run_check(app, DAY2, emails)
        # Day 3
        _run_check(app, DAY3, emails)

        assert len(emails) == 3, (
            f"Expected 3 daily reminders, got {len(emails)}"
        )

    def test_last_sent_date_advances_each_day(self, app, user_with_sub):
        emails = []
        _run_check(app, DAY1, emails)
        assert _get_last_sent(app) == DAY1.date()

        _run_check(app, DAY2, emails)
        assert _get_last_sent(app) == DAY2.date()

        _run_check(app, DAY3, emails)
        assert _get_last_sent(app) == DAY3.date()


class TestSameDayDeduplication:
    """The scheduler runs every hour; only one email may be sent per calendar day."""

    def test_no_duplicate_on_same_day(self, app, user_with_sub):
        emails = []
        # First run within the ±1h notification window
        _run_check(app, DAY1, emails)
        # Second run one hour later (still same calendar day)
        _run_check(app, DAY1_DUP, emails)

        assert len(emails) == 1, (
            f"Expected exactly 1 email on the same day, got {len(emails)}"
        )

    def test_outside_preferred_window_does_not_send(self, app, user_with_sub):
        """The scheduler should not send if the current hour is >1 h from the
        user's preferred notification hour (9:00)."""
        emails = []
        # 13:00 is 4 hours away from 09:00 – outside the ±1 h window
        _run_check(app, DAY1_FAR, emails)

        assert len(emails) == 0

    def test_send_after_failed_attempt_same_day(self, app, user_with_sub):
        """If the first send attempt fails the flag is reset, allowing a retry
        on the same day."""
        import app.email as email_mod

        emails = []

        def _fail(app_obj, user, subs):
            return False  # Simulate SMTP failure

        def _succeed(app_obj, user, subs):
            emails.append(user.username)
            return True

        fake_dt = _make_fake_datetime(DAY1)
        with patch("app.email.datetime", fake_dt):
            with patch.object(email_mod, "send_expiry_notification", side_effect=_fail):
                email_mod.check_expiring_subscriptions(app)

        # Flag should be reset to None after failure
        assert _get_last_sent(app) is None

        # Retry one hour later should succeed
        _run_check(app, DAY1_DUP, emails)
        assert len(emails) == 1


class TestStoppingBehavior:
    """No emails should be sent when the subscription has expired or is
    completely outside the notification window."""

    def test_no_email_after_expiration(self, app, user_with_sub):
        """Subscription expires 2026-04-06; no email on 2026-04-07."""
        emails = []
        # Send one legitimate email first to advance last_notification_sent
        _run_check(app, DAY5, emails)
        count_before = len(emails)

        # Day after expiry
        _run_check(app, DAY_AFTER_EXPIRY, emails)
        assert len(emails) == count_before, "No email expected after subscription expiry"

    def test_no_email_outside_window(self, app, user_with_sub):
        """Subscription expires 2026-04-06; 7-day window starts 2026-03-30.
        On 2026-03-28 (9 days before expiry) nothing should be sent."""
        emails = []
        _run_check(app, DAY_BEFORE_WINDOW, emails)
        assert len(emails) == 0, "No email expected when outside the notification window"

    def test_no_email_for_inactive_subscription(self, app, user_with_sub):
        from app.models import Subscription

        with app.app_context():
            from app import db
            sub = Subscription.query.filter_by(name="Netflix").first()
            sub.is_active = False
            db.session.commit()

        emails = []
        _run_check(app, DAY1, emails)
        assert len(emails) == 0, "No email expected for inactive subscription"

        # Restore
        with app.app_context():
            from app import db
            sub = Subscription.query.filter_by(name="Netflix").first()
            sub.is_active = True
            db.session.commit()


class TestNotificationDaysRobustness:
    """notification_days=None (possible for old DB rows) must not crash the
    scheduler; it should fall back to the default of 7."""

    def test_none_notification_days_falls_back_to_default(self, app, user_with_sub):
        from app.models import UserSettings

        # Force notification_days to None to mimic a legacy DB row
        with app.app_context():
            from app import db
            settings = UserSettings.query.filter_by().first()
            settings.notification_days = None
            db.session.commit()

        emails = []
        # Subscription expiring in 5 days is within the default 7-day window
        _run_check(app, DAY1, emails)

        assert len(emails) == 1, (
            "Expected notification when notification_days is None (should default to 7)"
        )

        # Restore
        with app.app_context():
            from app import db
            settings = UserSettings.query.filter_by().first()
            settings.notification_days = 7
            db.session.commit()


class TestTimezoneAwareScheduling:
    """Notifications should use the user's local date for both the
    preferred-time check and the same-day deduplication."""

    def test_user_in_positive_timezone(self, app, user_with_sub):
        """User is UTC+2.  A check at 07:00 UTC is 09:00 local – inside the
        window, so the email must be sent."""
        from app.models import UserSettings

        with app.app_context():
            from app import db
            settings = UserSettings.query.filter_by().first()
            settings.timezone = "Europe/Berlin"
            settings.notification_time = 9
            db.session.commit()

        emails = []
        # 07:00 UTC = 09:00 Europe/Berlin (CEST, UTC+2)
        _run_check(app, datetime(2026, 4, 1, 7, 0, tzinfo=timezone.utc), emails)
        assert len(emails) == 1

        # Restore
        with app.app_context():
            from app import db
            settings = UserSettings.query.filter_by().first()
            settings.timezone = "UTC"
            settings.notification_time = 9
            db.session.commit()
