"""Regression tests for month/year boundary handling in next billing date logic."""

from datetime import date

from app.models import Subscription


def _make_subscription(start_date, billing_cycle, **kwargs):
    return Subscription(
        name="Boundary Test",
        company="Example Co",
        cost=10.0,
        billing_cycle=billing_cycle,
        start_date=start_date,
        user_id=1,
        is_active=True,
        **kwargs,
    )


def test_monthly_31st_rolls_down_for_short_month():
    sub = _make_subscription(date(2026, 3, 31), "monthly")

    assert sub.get_next_billing_date(today=date(2026, 4, 1)) == date(2026, 4, 30)


def test_monthly_31st_returns_when_available_again():
    sub = _make_subscription(date(2026, 1, 31), "monthly")

    # Jan 31 -> Feb 28 -> Mar 31 (anchor day restored when valid)
    assert sub.get_next_billing_date(today=date(2026, 3, 1)) == date(2026, 3, 31)


def test_custom_monthly_preserves_anchor_day_behavior():
    sub = _make_subscription(
        date(2026, 1, 31),
        "custom",
        custom_period_value=1,
        custom_period_type="months",
    )

    assert sub.get_next_billing_date(today=date(2026, 3, 1)) == date(2026, 3, 31)


def test_yearly_leap_day_rolls_down_on_non_leap_years():
    sub = _make_subscription(date(2024, 2, 29), "yearly")

    assert sub.get_next_billing_date(today=date(2025, 1, 1)) == date(2025, 2, 28)


def test_yearly_leap_day_returns_on_next_leap_year():
    sub = _make_subscription(date(2024, 2, 29), "yearly")

    # 2025/2026/2027 clamp to Feb 28, then 2028 restores Feb 29.
    assert sub.get_next_billing_date(today=date(2027, 3, 1)) == date(2028, 2, 29)


def test_custom_yearly_leap_day_returns_on_next_leap_year():
    sub = _make_subscription(
        date(2024, 2, 29),
        "custom",
        custom_period_value=1,
        custom_period_type="years",
    )

    assert sub.get_next_billing_date(today=date(2027, 3, 1)) == date(2028, 2, 29)


def test_monthly_cycle_from_april_2025_returns_july_2026_on_july_2026_today():
    sub = _make_subscription(date(2025, 4, 18), "monthly")

    assert sub.get_next_billing_date(today=date(2026, 7, 15)) == date(2026, 7, 18)
