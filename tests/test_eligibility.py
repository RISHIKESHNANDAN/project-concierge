from datetime import date, timedelta

from app.tools.eligibility import cancel_check, refund_check
from app.tools.order_client import Order

P = {"return_window_days": "30", "manual_review_over_usd": "200"}


def order(status="delivered", days_ago=5, total=50.0):
    return Order(order_id="ORD-1", status=status, placed_at=date.today(), total=total, items=["x"],
                 delivered_at=date.today() - timedelta(days=days_ago) if status == "delivered" else None)


def test_within_window():
    assert refund_check(order(days_ago=10), params=P).startswith("eligible")


def test_outside_window():
    assert "NOT eligible" in refund_check(order(days_ago=45), params=P)


def test_boundary_day_30_is_eligible():
    assert refund_check(order(days_ago=30), params=P).startswith("eligible")


def test_large_order_manual_review():
    assert "manual review" in refund_check(order(total=250), params=P)


def test_not_delivered_and_cancel():
    assert "not yet applicable" in refund_check(order(status="shipped"), params=P)
    assert cancel_check(order(status="processing")).startswith("cancellable")
    assert "NOT cancellable" in cancel_check(order(status="shipped"))


def test_policy_params_come_from_active_docs():
    from app.tools.eligibility import policy_params
    assert policy_params()["return_window_days"] == "30"  # v1 (14 days) is superseded and ignored
