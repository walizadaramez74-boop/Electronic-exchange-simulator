from collections import defaultdict, deque


class OrderBook:
    def __init__(self):
        self.bids = defaultdict(deque)
        self.asks = defaultdict(deque)

    def add_order(self, order):
        if order.side == "BUY":
            self.bids[order.price].append(order)

        elif order.side == "SELL":
            self.asks[order.price].append(order)

        else:
            raise ValueError("Order side must be BUY or SELL")

    def best_bid(self):
        if not self.bids:
            return None

        return max(self.bids.keys())

    def best_ask(self):
        if not self.asks:
            return None

        return min(self.asks.keys())

    def cancel_order(self, order_id):
        for side in (self.bids, self.asks):
            for price in list(side.keys()):
                orders = side[price]

                for order in list(orders):
                    if order.order_id == order_id:
                        orders.remove(order)

                        if not orders:
                            del side[price]

                        return True

        return False