import httpx

from app.tools import order_client

GOOD = {"order_id": "ORD-1", "status": "shipped", "placed_at": "2026-01-01", "estimated_delivery": "2026-01-05",
        "delivered_at": None, "total": 10, "items": ["a"]}


class R:
    def __init__(self, code, body=None):
        self.status_code, self._b = code, body

    def json(self):
        return self._b


def patch(monkeypatch, responses):
    it = iter(responses)

    def fake(*a, **k):
        x = next(it)
        if isinstance(x, Exception):
            raise x
        return x
    monkeypatch.setattr(order_client.httpx, "get", fake)
    monkeypatch.setattr(order_client.time, "sleep", lambda s: None)


def test_ok(monkeypatch):
    patch(monkeypatch, [R(200, GOOD)])
    assert order_client.get_order("ORD-1", "a@b.c").outcome == "ok"


def test_retries_then_succeeds(monkeypatch):
    patch(monkeypatch, [R(503), httpx.ReadTimeout("t"), R(200, GOOD)])
    assert order_client.get_order("ORD-1", "a@b.c").outcome == "ok"


def test_unavailable_after_retries(monkeypatch):
    patch(monkeypatch, [R(503)] * 3)
    assert order_client.get_order("ORD-1", "a@b.c").outcome == "unavailable"


def test_malformed(monkeypatch):
    patch(monkeypatch, [R(200, {"order": "ORD-1", "state": "???"})])
    assert order_client.get_order("ORD-1", "a@b.c").outcome == "malformed"


def test_not_found_not_retried(monkeypatch):
    patch(monkeypatch, [R(404)])
    assert order_client.get_order("ORD-1", "a@b.c").outcome == "not_found"


def test_id_mismatch_is_malformed(monkeypatch):
    patch(monkeypatch, [R(200, {**GOOD, "order_id": "ORD-2"})])
    assert order_client.get_order("ORD-1", "a@b.c").outcome == "malformed"
