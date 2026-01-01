# Delta-Neutral Perp Arbitrage Bot (Paper-First)

What this repo does
- Paper-mode delta-neutral arbitrage: opens opposite perp positions on two connectors when spread exceeds a threshold.
- Modular connectors: includes a mock connector for paper/backtest. Swap in real DEX connectors later.
- Backtester supports CSV price feeds for each connector.
- Audit logging (CSV), safety limits (max exposure, cooldown), and configurable fees/slippage.

Get started
1. Copy `config.example.json` to `config.json` and edit.
2. Install deps:
   ```
   pip install -r requirements.txt
   ```
3. Run paper bot:
   ```
   python bot.py --config config.json
   ```
4. Run backtest (requires `historical_csv_a` and `_b` in config):
   ```
   python backtester.py --config config.json
   ```

Notes
- Default connectors are mocks. I can add real connector examples for specific perp DEXes (e.g., GMX on Arbitrum, Drift on Solana) if you tell me the exact DEX names and chain.
- This is a starter; thoroughly test and add safety checks before any live deployment.
