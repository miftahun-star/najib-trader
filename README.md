# NajibTrader — IHSG + US Stock Signal Scanner

Zero-cost-forever webapp that scans IHSG and US equities for bottom (buy) / peak (sell) signals using multi-indicator confluence scoring.

## Architecture

```
GitHub Actions (cron: 2x daily on market hours)
  → Python 3.11 engine: fetch OHLCV → compute indicators + scores → backtest
  → JSON output committed to data/
       ↓
Static Frontend (Cloudflare Pages / GitHub Pages)
  Vite + React, fetches JSON client-side
  Charts: TradingView lightweight-charts (MIT, self-hosted)
```

## Signal Engine (§3)

**Indicators computed per D/W/M timeframe:**
- RSI(14), Stochastic(14,3,3), MACD(12,26,9), Bollinger Bands(20,2), ATR(14)
- Volume vs 20-period average, Price vs MA50/MA200
- Bullish/Bearish divergence (price vs RSI/MACD)
- Reversal candle patterns (hammer, engulfing, morning/evening star, shooting star)
- Horizontal S/R levels (touched ≥2x within 1×ATR)
- Fibonacci retracement zone (38.2–61.8%)

**Composite Score (0–100):** Weighted confluence, never a single-indicator flip.
- ≥70 at range low → **BOTTOM (buy)**
- ≤30 at range high → **PEAK (sell)**
- 40–60 → **HOLD**
- else → **WATCH**

**Trade Levels:** ATR-based entry, SL (1.5×ATR), TP1/TP2/TP3 (1×/2×/3× risk), Chandelier trailing stop.

## Backtest

Every signal ships with its own live, continuously-updated backtested win-rate. Real transparent numbers — no marketing claims.

## Running Locally

```bash
# Python engine
pip install -r requirements.txt
python -m engine.run_scan

# Frontend
cd frontend
npm install
npm run dev
```

## Build Phases

- **Phase 0:** Skeleton — 5 tickers, basic indicators, JSON output ✅
- **Phase 1:** LQ45 + S&P 500, full scoring + backtest, frontend live
- **Phase 2:** Full IHSG (~950) + Russell, batching/rate-limit
- **Phase 3:** Telegram bot, per-ticker charts, mobile polish

## Disclaimer

⚠️ Algorithmic technical signals, not financial advice. Past performance ≠ future results. $0/month budget — all free-tier services.
