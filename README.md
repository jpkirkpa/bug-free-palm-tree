# Pocket Paper Trader — iPhone-friendly prototype

A Streamlit mobile web app that scans SPY, QQQ, AAPL, MSFT and NVDA and replays a simple long-only VWAP/EMA/volume strategy over recent 5-minute bars. **No broker connection, no real orders.**

## Deploy from your iPhone (no Python installation)
1. Create or sign into a GitHub account in Safari. Create a new **private or public** repository, e.g. `pocket-paper-trader`. (Streamlit Community Cloud availability and repo visibility requirements can change.)
2. Upload `app.py`, `requirements.txt`, and the `.streamlit/config.toml` file from this ZIP to the repository, keeping their folder paths. GitHub's mobile upload UI may require switching Safari to desktop website mode. You can skip `.streamlit/config.toml` if necessary; it only controls colors.
3. Visit https://share.streamlit.io and sign in with GitHub. Choose **Create app**, select your repository, branch `main`, and entrypoint `app.py`. Deploy.
4. Open the resulting URL in Safari. Use Share → Add to Home Screen.
5. Tap **Refresh market snapshot** for a fresh data request; Yahoo Finance can be delayed or unavailable.

## Local run (optional)
```bash
pip install -r requirements.txt
streamlit run app.py
```

## What this does / doesn't do
- **Does:** responsive scanner, indicators, hypothetical historical trade replay, simulated metrics, conservative stop-first handling when stop and target both hit in the same candle.
- **Does not:** run continuously in the background, send push alerts, execute live paper trades, persist account balances, use exchange-licensed real-time data, or place real trades.
- Simulations are **recomputed** on each run from the latest five trading days; they are not a persistent account ledger.
- Historical data from Yahoo Finance via yfinance may be delayed, incomplete, or unavailable; this is an experimental source.
- Backtest limitations: 5-minute candle resolution, no fees, spread, slippage, or taxes, no robustness validation. Signals can include a still-forming last candle.

## Future phase for truly unattended paper trading
Use a scheduled worker with a persistent database and a paper brokerage or licensed market data API, plus notifications. Hosting a Streamlit UI alone does not keep a strategy running when no one is viewing it. Never place real orders without explicit approval and extensive testing.
