import argparse
import json
import logging
import time
import csv
from connectors.mock_connector import MockConnector
from strategy import DeltaNeutralManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

CONNECTOR_MAP = {
    "mock_a": MockConnector,
    "mock_b": MockConnector
}

def load_config(path):
    with open(path, 'r') as f:
        return json.load(f)

def build_connector(name, cfg, connector_key):
    C = CONNECTOR_MAP.get(cfg[connector_key])
    if C is None:
        raise RuntimeError(f"No connector registered for {cfg[connector_key]}")
    # pass connector-specific cfg
    c_cfg = {"starting_balance_usd": cfg.get('starting_balances', {}).get(cfg[connector_key], 100.0),
            "initial_price": cfg.get('initial_price', 20000.0),
            "fee_pct": cfg.get('fee_pct', 0.00075),
            "slippage_pct": cfg.get('slippage_pct', 0.0005)}
    return C(cfg[connector_key], c_cfg)

def write_trade_log(path, event):
    header = ['timestamp','type','connector','order_id','side','size_usd','price','fee','spread','mid_a','mid_b']
    exists = False
    try:
        with open(path, 'r'):
            exists = True
    except FileNotFoundError:
        exists = False
    with open(path, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=header)
        if not exists:
            writer.writeheader()
        for o in event.get('orders', []):
            writer.writerow({
                'timestamp': time.time(),
                'type': event.get('type'),
                'connector': o.get('id', '').split('-')[0],
                'order_id': o.get('id'),
                'side': o.get('side'),
                'size_usd': o.get('size_usd'),
                'price': o.get('price'),
                'fee': o.get('fee'),
                'spread': event.get('spread'),
                'mid_a': event.get('mid_a'),
                'mid_b': event.get('mid_b')
            })

def main(config_path):
    cfg = load_config(config_path)
    # Build connectors
    conn_a = build_connector(cfg, cfg, 'connector_a')
    conn_b = build_connector(cfg, cfg, 'connector_b')

    manager = DeltaNeutralManager(cfg, conn_a, conn_b, logging)
    log_path = cfg.get('log_path', 'trades.csv')

    logging.info("Starting paper bot loop (Ctrl+C to stop)")
    try:
        while True:
            # If configured with CSV historical price override, set prices (optional)
            if cfg.get('historical_csv_a') and cfg.get('historical_csv_b'):
                # backtester mode is separate; here we assume live-ish mock price updated externally
                pass

            event = manager.step()
            if event:
                logging.info(f"Event: {event['type']} spread={event['spread']:.6f}")
                write_trade_log(log_path, event)
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Stopped by user")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='config.json')
    args = parser.parse_args()
    main(args.config)
