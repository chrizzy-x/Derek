from typing import Dict, Any

class BaseConnector:
    """
    Interface for connectors.
    Implement:
      - get_mid_price(pair) -> float
      - place_order(side, pair, size_usd, price=None) -> order dict
      - get_position(pair) -> dict {size_usd, side, entry_price}
      - cancel_order(order_id)
      - get_balance() -> float (USD stable balance for margin)
    """
    def __init__(self, name: str, cfg: Dict[str, Any]):
        self.name = name
        self.cfg = cfg

    def get_mid_price(self, pair: str) -> float:
        raise NotImplementedError

    def place_order(self, side: str, pair: str, size_usd: float, price: float = None) -> dict:
        raise NotImplementedError

    def get_position(self, pair: str) -> dict:
        raise NotImplementedError

    def cancel_order(self, order_id: str) -> None:
        raise NotImplementedError

    def get_balance(self) -> float:
        raise NotImplementedError
