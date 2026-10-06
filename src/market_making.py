"""Inventory-aware quoting and cash/inventory accounting for synthetic replay."""
from dataclasses import dataclass
import math


@dataclass
class Account:
    inventory: int = 0
    cash: float = 0.0
    average_cost: float = 0.0
    realised: float = 0.0
    fees: float = 0.0

    def fill(self, side, quantity, price, fee_per_unit=0.001):
        if side not in ('BUY', 'SELL') or quantity <= 0 or not math.isfinite(price) or price <= 0:
            raise ValueError('Invalid fill')
        if not math.isfinite(fee_per_unit) or fee_per_unit < 0:
            raise ValueError('Invalid fee')
        signed = quantity if side == 'BUY' else -quantity
        old = self.inventory
        if old == 0 or old*signed > 0:
            self.average_cost = (abs(old)*self.average_cost+quantity*price)/(abs(old)+quantity)
        else:
            closed = min(abs(old),quantity)
            self.realised += closed*(price-self.average_cost)*(1 if old > 0 else -1)
            if abs(signed)>abs(old):
                self.average_cost = price
            elif abs(signed)==abs(old):
                self.average_cost = 0.0
        self.inventory += signed
        fee = quantity*fee_per_unit
        self.fees += fee
        self.cash -= signed*price+fee

    def mark(self, mid):
        unrealised = self.inventory*(mid-self.average_cost)
        return dict(inventory=self.inventory, cash=self.cash,
                    realised_pnl=self.realised, unrealised_pnl=unrealised,
                    fees=self.fees, net_pnl=self.cash+self.inventory*mid)


@dataclass(frozen=True)
class QuoteConfig:
    clip: int = 20
    inventory_limit: int = 100
    half_spread: float = .02
    inventory_skew: float = .0003
    volatility_multiplier: float = .5

    def __post_init__(self):
        if self.clip <= 0 or self.inventory_limit <= 0:
            raise ValueError('Positive quantity and limit required')
        if not all(math.isfinite(x) and x>=0 for x in
                   (self.half_spread,self.inventory_skew,self.volatility_multiplier)) or self.half_spread==0:
            raise ValueError('Invalid quote configuration')


def quotes(mid, volatility, inventory, config):
    if not math.isfinite(mid) or mid<=0 or not math.isfinite(volatility) or volatility<0:
        raise ValueError('Invalid market inputs')
    centre = mid-config.inventory_skew*inventory
    half = config.half_spread+config.volatility_multiplier*volatility
    bid, ask = centre-half, centre+half
    buy_size = max(0,min(config.clip,config.inventory_limit-inventory))
    sell_size = max(0,min(config.clip,config.inventory_limit+inventory))
    return bid, ask, buy_size, sell_size
