"""SYNTHETIC order service: slow, flaky, occasionally malformed. Run: uvicorn mock_order_service.main:app --port 8001"""
import os
import random
import time
from datetime import date, timedelta

from fastapi import FastAPI, HTTPException

app = FastAPI(title="ShopEase mock order service")
FAIL = float(os.getenv("MOCK_FAIL_RATE", "0.2"))
SLOW = float(os.getenv("MOCK_SLOW_RATE", "0.1"))
BAD = float(os.getenv("MOCK_MALFORMED_RATE", "0.05"))
d = lambda n: (date.today() - timedelta(days=n)).isoformat()

ORDERS = {
    "ORD-1001": dict(email="alice@example.com", status="shipped", placed_at=d(9), estimated_delivery=d(3), delivered_at=None, total=89.0, items=["Headphones"]),
    "ORD-1002": dict(email="alice@example.com", status="delivered", placed_at=d(14), estimated_delivery=d(11), delivered_at=d(10), total=59.99, items=["Desk lamp"]),
    "ORD-1005": dict(email="alice@example.com", status="delivered", placed_at=d(6), estimated_delivery=d(3), delivered_at=d(2), total=250.0, items=["Monitor"]),
    "ORD-1003": dict(email="bob@example.com", status="processing", placed_at=d(1), estimated_delivery=d(-5), delivered_at=None, total=35.5, items=["Notebook set"]),
    "ORD-1004": dict(email="bob@example.com", status="delivered", placed_at=d(50), estimated_delivery=d(46), delivered_at=d(45), total=120.0, items=["Backpack"]),
    "ORD-1006": dict(email="bob@example.com", status="cancelled", placed_at=d(20), estimated_delivery=None, delivered_at=None, total=19.0, items=["Phone case"]),
}


@app.get("/")
def root():
    return {
        "service": "ShopEase mock order service",
        "health": "/health",
        "orders": "/orders/{order_id}?email=customer@example.com",
    }


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/orders/{order_id}")
def get_order(order_id: str, email: str):
    if random.random() < SLOW:
        time.sleep(5)  # longer than the client timeout
    if random.random() < FAIL:
        raise HTTPException(503, "upstream unavailable")
    if random.random() < BAD:
        return {"order": order_id, "state": "???"}
    o = ORDERS.get(order_id.upper())
    if not o or o["email"].lower() != email.lower():
        raise HTTPException(404, "order not found")  # same answer for missing and not-yours
    return {"order_id": order_id.upper(), **{k: v for k, v in o.items() if k != "email"}}
