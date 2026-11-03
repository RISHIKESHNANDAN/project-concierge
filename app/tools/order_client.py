"""Client for the (slow, flaky) order service. Never raises; always returns an OrderResult.
The customer's authenticated email is sent with every call so the service can reject
lookups for orders that belong to someone else."""
import time
from datetime import date
from typing import Literal, Optional

import httpx
from pydantic import BaseModel, ValidationError

from app.config import ORDER_RETRIES, ORDER_SERVICE_URL, ORDER_TIMEOUT_S


class Order(BaseModel):
    order_id: str
    status: Literal["processing", "shipped", "delivered", "cancelled"]
    placed_at: date
    estimated_delivery: Optional[date] = None
    delivered_at: Optional[date] = None
    total: float
    items: list[str]


class OrderResult(BaseModel):
    outcome: Literal["ok", "not_found", "unavailable", "malformed"]
    order: Optional[Order] = None
    detail: str = ""


def get_order(order_id: str, email: str) -> OrderResult:
    last = "unknown error"
    for attempt in range(ORDER_RETRIES):
        try:
            r = httpx.get(f"{ORDER_SERVICE_URL}/orders/{order_id}", params={"email": email},
                          timeout=ORDER_TIMEOUT_S)
        except httpx.HTTPError as e:  # timeouts, connection errors
            last = f"{type(e).__name__}"
        else:
            if r.status_code == 404:
                return OrderResult(outcome="not_found")
            if r.status_code == 200:
                try:
                    order = Order.model_validate(r.json())
                except (ValidationError, ValueError) as e:
                    return OrderResult(outcome="malformed", detail=str(e)[:200])
                if order.order_id.upper() != order_id.upper():
                    return OrderResult(outcome="malformed", detail="order id mismatch")
                return OrderResult(outcome="ok", order=order)
            last = f"HTTP {r.status_code}"
        time.sleep(0.3 * (2 ** attempt))
    return OrderResult(outcome="unavailable", detail=last)
