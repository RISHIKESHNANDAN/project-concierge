"""Deterministic policy checks. Thresholds are read from the ACTIVE policy documents' front
matter at call time, so editing a policy file (and re-ingesting it) changes behaviour
without code changes."""
from datetime import date
from typing import Optional

from app.config import DOCS_DIR
from app.ingestion.ingest import parse_document
from app.tools.order_client import Order


def policy_params() -> dict:
    params = {}
    for p in sorted(DOCS_DIR.glob("*.md")):
        meta, _ = parse_document(p.read_text(encoding="utf-8"))
        if meta.get("status") == "active":
            params.update({k: v for k, v in meta.items() if k in ("return_window_days", "manual_review_over_usd")})
    return params


def refund_check(order: Order, today: Optional[date] = None, params: Optional[dict] = None) -> str:
    today, params = today or date.today(), params or policy_params()
    window = int(params.get("return_window_days", 30))
    review = float(params.get("manual_review_over_usd", 200))
    if order.status == "cancelled":
        return "not applicable: order was cancelled (cancelled orders are refunded automatically)"
    if order.status != "delivered" or not order.delivered_at:
        return f"not yet applicable: order status is '{order.status}', returns start after delivery"
    days = (today - order.delivered_at).days
    if days > window:
        return f"NOT eligible: delivered {days} days ago, return window is {window} days"
    note = f"; total ${order.total:.2f} is over ${review:.0f} so manual review applies" if order.total > review else ""
    return f"eligible: delivered {days} days ago, within the {window}-day window{note}"


def cancel_check(order: Order) -> str:
    if order.status == "processing":
        return "cancellable: order has not shipped yet"
    if order.status == "cancelled":
        return "already cancelled"
    return f"NOT cancellable: order status is '{order.status}'"
