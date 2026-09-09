from dataclasses import dataclass
from typing import Optional


@dataclass
class Order:
    order_id: int
    side: str
    order_type: str
    quantity: int
    price: Optional[float]
    timestamp: int
