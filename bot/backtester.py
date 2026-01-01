import argparse
import json
import pandas as pd
from connectors.mock_connector import MockConnector
from strategy import DeltaNeutralManager
import logging
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

def load_config(path):
    with open(path, 'r') as f:
        return json.load(f)

def run_backtest(cfg):
    # requires CSV price feeds set in config: historical_csv_a and _b with columns: timestamp,price
    if not cfg.get('historical_csv_a') or not cfg.get('historical_csv_b'):
        raise RuntimeError("Set historical_csv_a and historical_csv_b in config for backtest")

    df_a = pd.read_csv(cfg['historical_csv_a'], parse_dates=['timestamp'])
    df_b = pd.read_csv(cfg['historical_csv_b'], parse_dates=['timestamp'])

    # align by timestamp (inner join)
    df = pd.merge_asof(df_a.sort_values('timestamp'), df_b.sort_values('timestamp'),
                       on='timestamp', direction='nearest', suffixes=('_a','_b'))

    # create mock connectors
    conn_a = MockConnector(cfg['connector_a'], {"starting_balance_usd": cfg['starting_balances'].get(cfg['connector_a'],100.0),
                                               "initial_price": df['price_a'].iloc[0],
                                               "fee_pct": cfg.get('fee_pct',0.00075),
                                               "slippage_pct": cfg.get('slippage_pct',0.0005)})
    conn_b = MockConnector(cfg['connector_b'], {"starting_balance_usd": cfg['starting_balances'].get(cfg['connector_b'],100.0),
                                               "initial_price": df['price_b'].iloc[0],
                                               "fee_pct": cfg.get('fee_pct',0.00075),
                                               "slippage_pct": cfg.get('slippage_pct',0.0005)})
    manager = DeltaNeutralManager(cfg, conn_a, conn_b, logging)

    events = []
    for _, row in df.iterrows():
        conn_a.set_price(row['price_a'])
        conn_b.set_price(row['price_b'])
        event = manager.step()
        if event:
            events.append(event)
        # small time progression
        time.sleep(0.0001)
    # Summary
    print("Backtest finished. Trades:", len(events))
    # print final positions/balances
    print("Conn A balance:", conn_a.get_balance(), "position:", conn_a.get_position(cfg['pair']))
    print("Conn B balance:", conn_b.get_balance(), "position:", conn_b.get_position(cfg['pair']))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='config.json')
    args = parser.parse_args()
    cfg = load_config(args.config)
    run_backtest(cfg)
