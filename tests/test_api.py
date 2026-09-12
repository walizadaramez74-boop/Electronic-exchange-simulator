from fastapi.testclient import TestClient

from api import app


client = TestClient(app)


def reset_exchange():
    response = client.post("/reset")
    assert response.status_code == 200


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_submit_limit_order_updates_order_book():
    reset_exchange()

    response = client.post(
        "/orders",
        json={
            "side": "BUY",
            "order_type": "LIMIT",
            "quantity": 100,
            "price": 99.95
        }
    )

    assert response.status_code == 200
    assert response.json()["order_id"] == 1
    assert response.json()["remaining_quantity"] == 100

    book = client.get("/orderbook")

    assert book.status_code == 200

    data = book.json()

    assert data["best_bid"] == 99.95
    assert data["best_ask"] is None
    assert data["bids"][0]["total_quantity"] == 100


def test_market_order_creates_trade():
    reset_exchange()

    client.post(
        "/orders",
        json={
            "side": "SELL",
            "order_type": "LIMIT",
            "quantity": 100,
            "price": 100.05
        }
    )

    response = client.post(
        "/orders",
        json={
            "side": "BUY",
            "order_type": "MARKET",
            "quantity": 40,
            "price": None
        }
    )

    assert response.status_code == 200

    result = response.json()

    assert result["remaining_quantity"] == 0
    assert len(result["trades"]) == 1

    trade = result["trades"][0]

    assert trade["price"] == 100.05
    assert trade["quantity"] == 40

    book = client.get("/orderbook").json()

    assert book["best_ask"] == 100.05
    assert book["asks"][0]["total_quantity"] == 60


def test_cancel_order():
    reset_exchange()

    order_response = client.post(
        "/orders",
        json={
            "side": "BUY",
            "order_type": "LIMIT",
            "quantity": 50,
            "price": 99.50
        }
    )

    order_id = order_response.json()["order_id"]

    response = client.delete(
        f"/orders/{order_id}"
    )

    assert response.status_code == 200
    assert response.json()["cancelled_order_id"] == order_id

    book = client.get("/orderbook").json()

    assert book["best_bid"] is None
    assert book["bids"] == []


def test_limit_order_requires_price():
    reset_exchange()

    response = client.post(
        "/orders",
        json={
            "side": "BUY",
            "order_type": "LIMIT",
            "quantity": 100,
            "price": None
        }
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Limit orders require a price."

