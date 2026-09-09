from order import Order
from order_book import OrderBook


def test_best_bid_and_ask():
    book = OrderBook()

    buy_1 = Order(1, "BUY", "LIMIT", 50, 99.0, 1)
    buy_2 = Order(2, "BUY", "LIMIT", 50, 100.0, 2)

    sell_1 = Order(3, "SELL", "LIMIT", 50, 102.0, 3)
    sell_2 = Order(4, "SELL", "LIMIT", 50, 101.0, 4)

    book.add_order(buy_1)
    book.add_order(buy_2)
    book.add_order(sell_1)
    book.add_order(sell_2)

    assert book.best_bid() == 100.0
    assert book.best_ask() == 101.0


def test_time_priority_at_same_price():
    book = OrderBook()

    first_order = Order(1, "BUY", "LIMIT", 50, 100.0, 1)
    second_order = Order(2, "BUY", "LIMIT", 50, 100.0, 2)

    book.add_order(first_order)
    book.add_order(second_order)

    assert book.bids[100.0][0].order_id == 1
    assert book.bids[100.0][1].order_id == 2