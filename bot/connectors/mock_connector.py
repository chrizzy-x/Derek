import time
import random
from .base_connector import BaseConnector

class MockConnector(BaseConnector):
    """
    Simple simulated perp connector for paper trading and backtesting.
    - mid price can be advanced by set_price() or read from CSV in backtester.
    - positions are stored as a single notional entry per pair.
    """

    def __init__(self, name, cfg):
        super().__init__(name, cfg)
        self._price = float(cfg.get('initial_price', 20000.0))
        self._position = {"size_usd": 0.0, "side": None, "entry_price": None}
        self._balance = float(cfg.get('starting_balance_usd', 100.0))
        self._last_order_id = 0
        self.fee_pct = cfg.get('fee_pct', 0.00075)
        self.slippage_pct = cfg.get('slippage_pct', 0.0005)

    def set_price(self, price: float):
        self._price = float(price)

    def get_mid_price(self, pair: str) -> float:
        # add small random micro-moves for realism
        noise = random.uniform(-0.0001, 0.0001) * self._price
        return max(0.01, self._price + noise)

    def place_order(self, side: str, pair: str, size_usd: float, price: float = None) -> dict:
        self._last_order_id += 1
        order_id = f"{self.name}-order-{self._last_order_id}"
        mid = self.get_mid_price(pair) if price is None else price
        # simulate slippage
        sign = 1 if side == 'buy' else -1
        exec_price = mid * (1 + sign * self.slippage_pct)
        # update position as perp with notional size in USD
        # if same side, increase; if opposite side, reduce/flip
        if self._position['size_usd'] == 0:
            self._position = {"size_usd": size_usd, "side": side, "entry_price": exec_price}
        else:
            if self._position['side'] == side:
                # average entry price weighted by USD notional
                old_nv = self._position['size_usd']
                new_nv = old_nv + size_usd
                avg = (old_nv * self._position['entry_price'] + size_usd * exec_price) / new_nv
                self._position = {"size_usd": new_nv, "side": side, "entry_price": avg}
            else:
                # reduce opposite exposure
                if size_usd < self._position['size_usd']:
                    self._position['size_usd'] -= size_usd
                    # entry_price unchanged for remaining
                else:
                    # flip side
                    leftover = size_usd - self._position['size_usd']
                    self._position = {"size_usd": leftover, "side": side, "entry_price": exec_price}
        # adjust balance by fees (simplified)
        fee = abs(size_usd) * self.fee_pct
        self._balance -= fee
        return {"id": order_id, "price": exec_price, "size_usd": size_usd, "side": side, "fee": fee, "timestamp": time.time()}

    def get_position(self, pair: str) -> dict:
        return dict(self._position)

    def cancel_order(self, order_id: str) -> None:
        # mock: nothing to do
        return

    def get_balance(self) -> float:
        return float(self._balance)
