import random
import csv
from statistics import mean

from order import Order
from matching_engine import MatchingEngine


def build_order_book(scenario):
    engine = MatchingEngine()
    order_id = 1

    best_bid = 99.95
    best_ask = 100.05
    levels = 10

    if scenario == "DEEP":
        quantity_per_level = 250
        price_step = 0.05

    elif scenario == "THIN":
        quantity_per_level = 75
        price_step = 0.15

    else:
        raise ValueError("Scenario must be DEEP or THIN")

    for level in range(levels):
        price = round(best_bid - level * price_step, 2)

        order = Order(
            order_id=order_id,
            side="BUY",
            order_type="LIMIT",
            quantity=quantity_per_level,
            price=price,
            timestamp=order_id
        )

        engine.process_order(order)
        order_id += 1

    for level in range(levels):
        price = round(best_ask + level * price_step, 2)

        order = Order(
            order_id=order_id,
            side="SELL",
            order_type="LIMIT",
            quantity=quantity_per_level,
            price=price,
            timestamp=order_id
        )

        engine.process_order(order)
        order_id += 1

    return engine


def execute_market_order(scenario, side, quantity):
    engine = build_order_book(scenario)

    best_bid = engine.order_book.best_bid()
    best_ask = engine.order_book.best_ask()

    market_order = Order(
        order_id=1000,
        side=side,
        order_type="MARKET",
        quantity=quantity,
        price=None,
        timestamp=1000
    )

    trades_before = len(engine.trades)

    engine.process_order(market_order)

    trades = engine.trades[trades_before:]

    executed_quantity = sum(
        trade.quantity for trade in trades
    )

    if executed_quantity == 0:
        return None

    total_value = sum(
        trade.price * trade.quantity
        for trade in trades
    )

    average_execution_price = total_value / executed_quantity

    if side == "BUY":
        slippage = average_execution_price - best_ask
    else:
        slippage = best_bid - average_execution_price

    return {
        "scenario": scenario,
        "side": side,
        "quantity": quantity,
        "executed_quantity": executed_quantity,
        "average_execution_price": average_execution_price,
        "slippage": slippage,
        "fully_filled": executed_quantity == quantity
    }


def size_bucket(quantity):
    if quantity <= 50:
        return "SMALL"

    elif quantity <= 150:
        return "MEDIUM"

    else:
        return "LARGE"


def run_experiment(scenario, number_of_orders=10000, seed=42):
    rng = random.Random(seed)
    results = []

    for _ in range(number_of_orders):
        side = rng.choice(["BUY", "SELL"])
        quantity = rng.randint(10, 400)

        result = execute_market_order(
            scenario,
            side,
            quantity
        )

        if result is not None:
            result["size"] = size_bucket(quantity)
            results.append(result)

    return results


def summarise(results):
    summary = []

    for scenario in ["DEEP", "THIN"]:

        scenario_results = [
            result
            for result in results
            if result["scenario"] == scenario
        ]

        for bucket in ["SMALL", "MEDIUM", "LARGE"]:

            bucket_results = [
                result
                for result in scenario_results
                if result["size"] == bucket
            ]

            if not bucket_results:
                continue

            average_slippage = mean(
                result["slippage"]
                for result in bucket_results
            )

            average_quantity = mean(
                result["quantity"]
                for result in bucket_results
            )

            fill_rate = mean(
                result["fully_filled"]
                for result in bucket_results
            )

            summary.append({
                "scenario": scenario,
                "size": bucket,
                "observations": len(bucket_results),
                "average_quantity": average_quantity,
                "average_slippage": average_slippage,
                "fill_rate": fill_rate
            })

    return summary


def print_summary(summary):
    print()
    print("LIQUIDITY EXPERIMENT")
    print("====================")

    for result in summary:
        print()
        print(result["scenario"], "-", result["size"])
        print("Observations:", result["observations"])
        print(
            "Average order size:",
            round(result["average_quantity"], 2)
        )
        print(
            "Average slippage:",
            round(result["average_slippage"], 5)
        )
        print(
            "Full-fill rate:",
            round(result["fill_rate"] * 100, 2),
            "%"
        )


def save_summary(summary):
    filename = "analysis/liquidity_results.csv"

    fields = [
        "scenario",
        "size",
        "observations",
        "average_quantity",
        "average_slippage",
        "fill_rate"
    ]

    with open(filename, "w", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fields
        )

        writer.writeheader()
        writer.writerows(summary)

    print()
    print("Results saved to:", filename)


if __name__ == "__main__":
    deep_results = run_experiment(
        "DEEP",
        number_of_orders=10000,
        seed=42
    )

    thin_results = run_experiment(
        "THIN",
        number_of_orders=10000,
        seed=42
    )

    all_results = deep_results + thin_results

    summary = summarise(all_results)

    print_summary(summary)
    save_summary(summary)
