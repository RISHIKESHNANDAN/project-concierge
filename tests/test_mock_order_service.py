from fastapi.testclient import TestClient

from mock_order_service.main import app

client = TestClient(app)


def test_root_describes_service_endpoints():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "service": "ShopEase mock order service",
        "health": "/health",
        "orders": "/orders/{order_id}?email=customer@example.com",
    }
