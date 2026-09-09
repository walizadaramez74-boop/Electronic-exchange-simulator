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

def test_market_buy_order():
    engine = MatchingEngine()

    sell_1 = Order(1, "SELL", "LIMIT", 50, 100.0, 1)
    sell_2 = Order(2, "SELL", "LIMIT", 50, 101.0, 2)

    engine.process_order(sell_1)
    engine.process_order(sell_2)

    market_buy = Order(3, "BUY", "MARKET", 70, None, 3)

    engine.process_order(market_buy)

    assert len(engine.trades) == 2

    assert engine.trades[0].sell_order_id == 1
    assert engine.trades[0].price == 100.0
    assert engine.trades[0].quantity == 50

    assert engine.trades[1].sell_order_id == 2
    assert engine.trades[1].price == 101.0
    assert engine.trades[1].quantity == 20

    assert engine.order_book.asks[101.0][0].quantity == 30


def test_market_sell_order():
    engine = MatchingEngine()

    buy_1 = Order(1, "BUY", "LIMIT", 50, 100.0, 1)
    buy_2 = Order(2, "BUY", "LIMIT", 50, 99.0, 2)

    engine.process_order(buy_1)
    engine.process_order(buy_2)

    market_sell = Order(3, "SELL", "MARKET", 70, None, 3)

    engine.process_order(market_sell)

    assert len(engine.trades) == 2

    assert engine.trades[0].buy_order_id == 1
    assert engine.trades[0].price == 100.0
    assert engine.trades[0].quantity == 50

    assert engine.trades[1].buy_order_id == 2
    assert engine.trades[1].price == 99.0
    assert engine.trades[1].quantity == 20

    assert engine.order_book.bids[99.0][0].quantity == 30


def test_unfilled_market_order_does_not_rest():
    engine = MatchingEngine()

    sell_order = Order(1, "SELL", "LIMIT", 30, 100.0, 1)
    engine.process_order(sell_order)

    market_buy = Order(2, "BUY", "MARKET", 50, None, 2)
    engine.process_order(market_buy)

    assert len(engine.trades) == 1
    assert engine.trades[0].quantity == 30

    assert market_buy.quantity == 20
    assert not engine.order_book.bids
    assert not engine.order_book.asks
