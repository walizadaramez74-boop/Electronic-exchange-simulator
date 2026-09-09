from order import Order
from matching_engine import MatchingEngine


def test_partial_fill():
    engine = MatchingEngine()

    buy_order = Order(1, "BUY", "LIMIT", 100, 100.0, 1)
    sell_order = Order(2, "SELL", "LIMIT", 40, 99.0, 2)

    engine.process_order(buy_order)
    engine.process_order(sell_order)

    assert len(engine.trades) == 1
    assert engine.trades[0].quantity == 40
    assert engine.trades[0].price == 100.0

    remaining_order = engine.order_book.bids[100.0][0]

    assert remaining_order.quantity == 60


def test_time_priority():
    engine = MatchingEngine()

    buy_1 = Order(1, "BUY", "LIMIT", 50, 100.0, 1)
    buy_2 = Order(2, "BUY", "LIMIT", 50, 100.0, 2)
    sell = Order(3, "SELL", "LIMIT", 60, 100.0, 3)

    engine.process_order(buy_1)
    engine.process_order(buy_2)
    engine.process_order(sell)

    assert len(engine.trades) == 2

    assert engine.trades[0].buy_order_id == 1
    assert engine.trades[0].quantity == 50

    assert engine.trades[1].buy_order_id == 2
    assert engine.trades[1].quantity == 10

    remaining_order = engine.order_book.bids[100.0][0]

    assert remaining_order.order_id == 2
    assert remaining_order.quantity == 40


def test_price_priority():
    engine = MatchingEngine()

    buy_1 = Order(1, "BUY", "LIMIT", 50, 99.0, 1)
    buy_2 = Order(2, "BUY", "LIMIT", 50, 100.0, 2)
    sell = Order(3, "SELL", "LIMIT", 40, 99.0, 3)

    engine.process_order(buy_1)
    engine.process_order(buy_2)
    engine.process_order(sell)

    assert len(engine.trades) == 1
    assert engine.trades[0].buy_order_id == 2
    assert engine.trades[0].quantity == 40
    assert engine.trades[0].price == 100.0

    assert engine.order_book.bids[100.0][0].quantity == 10
    assert engine.order_book.bids[99.0][0].quantity == 50