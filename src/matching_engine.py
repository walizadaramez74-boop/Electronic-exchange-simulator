from order import Order
from trade import Trade
from order_book import OrderBook


class MatchingEngine:
    def __init__(self):
        self.order_book = OrderBook()
        self.trades = []

    def process_order(self, order):

        if order.side == "BUY":
            self._process_buy_order(order)

        elif order.side == "SELL":
            self._process_sell_order(order)

        else:
            raise ValueError("Order side must be BUY or SELL")

    def _process_buy_order(self, order):

        while order.quantity > 0 and self.order_book.asks:

            best_ask = self.order_book.best_ask()

            if order.order_type == "LIMIT" and order.price < best_ask:
                break

            resting_order = self.order_book.asks[best_ask][0]

            trade_quantity = min(
                order.quantity,
                resting_order.quantity
            )

            trade = Trade(
                buy_order_id=order.order_id,
                sell_order_id=resting_order.order_id,
                price=best_ask,
                quantity=trade_quantity
            )

            self.trades.append(trade)

            order.quantity -= trade_quantity
            resting_order.quantity -= trade_quantity

            if resting_order.quantity == 0:
                self.order_book.asks[best_ask].popleft()

                if not self.order_book.asks[best_ask]:
                    del self.order_book.asks[best_ask]

        if order.quantity > 0 and order.order_type == "LIMIT":
            self.order_book.add_order(order)

    def _process_sell_order(self, order):

        while order.quantity > 0 and self.order_book.bids:

            best_bid = self.order_book.best_bid()

            if order.order_type == "LIMIT" and order.price > best_bid:
                break

            resting_order = self.order_book.bids[best_bid][0]

            trade_quantity = min(
                order.quantity,
                resting_order.quantity
            )

            trade = Trade(
                buy_order_id=resting_order.order_id,
                sell_order_id=order.order_id,
                price=best_bid,
                quantity=trade_quantity
            )

            self.trades.append(trade)

            order.quantity -= trade_quantity
            resting_order.quantity -= trade_quantity

            if resting_order.quantity == 0:
                self.order_book.bids[best_bid].popleft()

                if not self.order_book.bids[best_bid]:
                    del self.order_book.bids[best_bid]

        if order.quantity > 0 and order.order_type == "LIMIT":
            self.order_book.add_order(order)
