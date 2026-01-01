from typing import Dict, Any
import time

def compute_spread(mid_a: float, mid_b: float) -> float:
    # spread as (A - B) / midpoint; signed
    mid = (mid_a + mid_b) / 2.0
    if mid == 0:
        return 0.0
    return (mid_a - mid_b) / mid

class DeltaNeutralManager:
    """
    Strategy manager that:
    - Monitors mid prices on two connectors
    - When spread magnitude > min_spread_pct, opens opposite notional positions
      sized to be delta-neutral (same USD notional, opposite sides)
    - Exit when spread compresses below take_profit_spread_pct
    - Honors max exposure and cooldown
    """

    def __init__(self, cfg: Dict[str, Any], conn_a, conn_b, logger):
        self.cfg = cfg
        self.a = conn_a
        self.b = conn_b
        self.logger = logger
        self.last_trade_time = 0

    def should_open(self, spread: float) -> bool:
        return abs(spread) >= float(self.cfg.get('min_spread_pct', 0.002))

    def should_close(self, spread: float) -> bool:
        return abs(spread) <= float(self.cfg.get('take_profit_spread_pct', 0.0005))

    def get_current_exposure(self):
        pa = self.a.get_position(self.cfg['pair'])
        pb = self.b.get_position(self.cfg['pair'])
        return pa.get('size_usd', 0.0) + pb.get('size_usd', 0.0)

    def step(self):
        pair = self.cfg['pair']
        mid_a = self.a.get_mid_price(pair)
        mid_b = self.b.get_mid_price(pair)
        spread = compute_spread(mid_a, mid_b)
        now = time.time()
        cooldown = self.cfg.get('cooldown_seconds', 60)

        # Safety: cooldown between opening trades
        if now - self.last_trade_time < cooldown:
            return None

        # Try to open delta-neutral pair if spread is large and exposure permits
        if self.should_open(spread):
            order_size = float(self.cfg.get('order_size_usd', 100.0))
            max_ex = float(self.cfg.get('max_exposure_usd', 1000.0))
            curr_ex = self.get_current_exposure()
            if curr_ex + 2 * order_size > max_ex:
                self.logger.info("Max exposure would be exceeded; skipping open.")
                return None

            # Determine which side on which exchange
            # If spread > 0 => price A > B, go short A, long B to capture convergence
            if spread > 0:
                side_a = 'sell'
                side_b = 'buy'
            else:
                side_a = 'buy'
                side_b = 'sell'

            # Place orders simultaneously (best-effort)
            o_a = self.a.place_order(side_a, pair, order_size)
            o_b = self.b.place_order(side_b, pair, order_size)
            self.last_trade_time = now
            return {"type": "open", "spread": spread, "orders": [o_a, o_b], "mid_a": mid_a, "mid_b": mid_b}

        # If we have exposure and spread tightened, close
        pa = self.a.get_position(pair)
        pb = self.b.get_position(pair)
        if (pa.get('size_usd', 0.0) > 0 or pb.get('size_usd', 0.0) > 0) and self.should_close(spread):
            # Close both sides by placing opposite orders equal to notional
            orders = []
            if pa.get('size_usd', 0.0) > 0:
                close_side = 'buy' if pa['side'] == 'sell' else 'sell'
                orders.append(self.a.place_order(close_side, pair, pa['size_usd']))
            if pb.get('size_usd', 0.0) > 0:
                close_side = 'buy' if pb['side'] == 'sell' else 'sell'
                orders.append(self.b.place_order(close_side, pair, pb['size_usd']))
            self.last_trade_time = now
            return {"type": "close", "spread": spread, "orders": orders, "mid_a": mid_a, "mid_b": mid_b}

        return None
