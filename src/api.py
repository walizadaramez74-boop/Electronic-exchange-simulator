from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from order import Order
from matching_engine import MatchingEngine


app = FastAPI(
    title="Electronic Exchange Simulator API",
    description="REST API for submitting orders to a simulated electronic exchange.",
    version="1.0.0"
)
app.mount(
    "/static",
    StaticFiles(directory="src/static"),
    name="static"
)


@app.get("/", include_in_schema=False)
def homepage():
    return FileResponse("src/static/index.html")
engine = MatchingEngine()
next_order_id = 1


class OrderRequest(BaseModel):
    side: Literal["BUY", "SELL"]
    order_type: Literal["LIMIT", "MARKET"]
    quantity: int = Field(gt=0)
    price: Optional[float] = Field(default=None, gt=0)


def serialise_order(order):
    return {
        "order_id": order.order_id,
        "side": order.side,
        "order_type": order.order_type,
        "quantity": order.quantity,
        "price": order.price,
        "timestamp": order.timestamp
    }


def serialise_trade(trade):
    return {
        "buy_order_id": trade.buy_order_id,
        "sell_order_id": trade.sell_order_id,
        "price": trade.price,
        "quantity": trade.quantity
    }


@app.get("/health")
def health():
    return {
        "status": "ok"
    }


@app.post("/orders")
def submit_order(request: OrderRequest):
    global next_order_id

    if request.order_type == "LIMIT" and request.price is None:
        raise HTTPException(
            status_code=400,
            detail="Limit orders require a price."
        )

    if request.order_type == "MARKET" and request.price is not None:
        raise HTTPException(
            status_code=400,
            detail="Market orders should not include a price."
        )

    order = Order(
        order_id=next_order_id,
        side=request.side,
        order_type=request.order_type,
        quantity=request.quantity,
        price=request.price,
        timestamp=next_order_id
    )

    next_order_id += 1

    trades_before = len(engine.trades)

    engine.process_order(order)

    new_trades = engine.trades[trades_before:]

    return {
        "order_id": order.order_id,
        "remaining_quantity": order.quantity,
        "trades": [
            serialise_trade(trade)
            for trade in new_trades
        ]
    }


@app.delete("/orders/{order_id}")
def cancel_order(order_id: int):
    cancelled = engine.cancel_order(order_id)

    if not cancelled:
        raise HTTPException(
            status_code=404,
            detail="Order not found."
        )

    return {
        "cancelled_order_id": order_id
    }


@app.get("/orderbook")
def get_order_book():
    bids = []
    asks = []

    for price in sorted(
        engine.order_book.bids.keys(),
        reverse=True
    ):
        orders = engine.order_book.bids[price]

        bids.append({
            "price": price,
            "total_quantity": sum(
                order.quantity for order in orders
            ),
            "orders": [
                serialise_order(order)
                for order in orders
            ]
        })

    for price in sorted(
        engine.order_book.asks.keys()
    ):
        orders = engine.order_book.asks[price]

        asks.append({
            "price": price,
            "total_quantity": sum(
                order.quantity for order in orders
            ),
            "orders": [
                serialise_order(order)
                for order in orders
            ]
        })

    return {
        "best_bid": engine.order_book.best_bid(),
        "best_ask": engine.order_book.best_ask(),
        "bids": bids,
        "asks": asks
    }


@app.get("/trades")
def get_trades():
    return [
        serialise_trade(trade)
        for trade in engine.trades
    ]


@app.post("/reset")
def reset_exchange():
    global engine
    global next_order_id

    engine = MatchingEngine()
    next_order_id = 1

    return {
        "status": "exchange reset"
    }
