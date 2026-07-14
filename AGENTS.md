# AGENTS.md — IHSG + US Stock Bottom/Peak Signal Scanner
Drop this file at the root of a new project folder. Antigravity CLI reads AGENTS.md automatically and prepends it to every prompt in that directory. First command to give it: **"Start Phase 0 from AGENTS.md."**

## 0. Reality check — non-negotiable, overrides any conflicting instruction below
No system can hit 100% or even 90–99% accuracy predicting market tops/bottoms — not this app, not a Bloomberg terminal, not the best quant funds (which run ~55–60% win rate and make money on risk:reward, not on being "right"). Any task in this repo that implies otherwise must be reinterpreted as follows:
- **Never** ship UI copy, README text, or code comments claiming "100% akurat," "sempurna," or any fixed accuracy %.
- **Instead:** every signal ships with its own live, continuously-updated backtested win-rate (§4). A real, transparent number is the only honest version of "akurat" this project can deliver — build that, not a marketing claim.

## 1. Goal
Zero-cost-forever webapp that:
- Scans IHSG (Phase 1: LQ45+IDX30 → Phase 2: full ~950-ticker universe) and US equities (Phase 1: S&P 500 + Nasdaq 100 → Phase 2: Russell 3000)
- Flags bottom (buy) / peak (sell) / hold signals per ticker on Daily, Weekly, Monthly, with a Yearly trend overlay
- Every active signal ships exact entry, stop loss, TP1/TP2/TP3, trailing stop — formula-driven (§3), never eyeballed
- Shows a transparent backtest/track-record panel (§4)
- Optional Telegram push on new signals

## 2. Architecture & stack
Vercel Hobby cron caps at once/day and functions time out in ~10s — useless for scanning 1000+ tickers. **GitHub Actions on a public repo has unlimited free minutes on standard Linux runners — that's the compute engine, not Vercel.**

```
[GitHub Actions cron, e.g. */15 2-9,13-21 * * 1-5 UTC — tune to actual IDX/US session hours + DST]
  Python 3.11: fetch OHLCV -> compute indicators+scores -> refresh backtest
  -> write JSON (data/signals/*.json, data/backtest.json) -> commit
        |  static files only, no live backend, nothing to keep "on"
        v
[Static frontend: Cloudflare Pages (primary) or GitHub Pages (fallback)]
  Vite + React + Tailwind, static build, fetch JSON client-side
  Charts: TradingView `lightweight-charts` (OSS/MIT, self-hosted -- NOT tradingview.com)
        |  optional
        v
[Telegram Bot API -> push new-signal alerts]
```

## 3. Signal engine — exact spec
### 3.1 Indicators (per timeframe D/W/M, computed independently)
RSI(14), Stochastic(14,3,3), MACD(12,26,9), Bollinger Bands(20,2), ATR(14), volume vs 20-period avg, price vs MA50/MA200; bullish/bearish divergence (price vs RSI/MACD over last 2 swing points); reversal candle at the extreme (hammer/engulfing/morning star = bottom, shooting star/engulfing/evening star = peak); horizontal S/R (price within 1×ATR of a level touched ≥2x); Fibonacci retracement zone (38.2–61.8%).

### 3.2 Composite score (0–100, weighted confluence — never a single-indicator flip)
RSI/Stoch extreme 20%, divergence 25%, candle pattern 15%, BB touch 15%, volume climax 10%, S/R or Fib confluence 15%. Weights are a starting point — agent must re-tune against backtest results in §4 and document final weights in code.
- ≥70 at range low → **BOTTOM (buy)**
- ≤30 at range high → **PEAK (sell)**
- 40–60 → **HOLD/neutral**
- else → **WATCH**

### 3.3 Trade levels — ATR-based, per-ticker, never a flat %
- Entry = signal candle close (log next-session open too for comparison)
- Long/bottom: SL = Entry − 1.5×ATR14 · Risk = Entry−SL · TP1 = Entry+1×Risk · TP2 = +2×Risk · TP3 = +3×Risk or nearest resistance/Fib extension, whichever is closer
- Short/peak: mirror the above
- Trailing stop (Chandelier-style): once price moves ≥1×ATR in favor, trail_stop = highest-high-since-entry − k×ATR14 (long) or lowest-low + k×ATR14 (short), k=2–3 tuned via backtest; ratchets toward profit only, never loosens
- Every signal displays its R:R ratio

### 3.4 Timeframe honesty
Daily/Weekly/Monthly = full reversal-signal logic above, run independently per timeframe. **Yearly is trend structure, not a reversal call** — show price vs weekly-MA200 and higher-high/higher-low vs lower-high/lower-low structure, labeled "long-term trend bias." Do not fabricate yearly reversal precision that doesn't exist.

## 4. Backtest / track record — this is the actual answer to "akurat"
Use `backtesting.py` or `vectorbt` (free, OSS) to replay the exact live signal logic on historical data, per ticker and in aggregate. Recompute nightly in the same Action. Publish win rate, avg R-multiple, max drawdown, sample size — segmented by market (IHSG/US) and timeframe. Every signal card in the UI pulls its "X% historically, n=Y trades" from this file. That's the real number, not an assertion.

## 5. Free-tier resource map
| Layer | Service | Free limit that matters | Note |
|---|---|---|---|
| Compute/cron | **GitHub Actions**, public repo | Unlimited minutes, standard Linux runner | The whole engine runs here, not on Vercel |
| Data — IHSG & US | `yfinance` (Yahoo, unofficial) | No published cap; batch + throttle or risk temp IP block | `.JK` suffix for IDX (BBCA.JK, TLKM.JK…), `^JKSE` for the index |
| Data backup | Stooq.com CSV endpoint | No key, no official cap | Fallback when Yahoo hiccups |
| Data backup (US) | Finnhub free | 60 calls/min | Also has earnings/news |
| Data backup (US/global) | Twelve Data free | 800 req/day, 8/min | Some ID coverage too |
| ~~Alpha Vantage~~ | — | **25 req/day only as of 2026** | Too small to be useful here — skip it |
| Frontend hosting | Cloudflare Pages / GitHub Pages | Effectively unlimited static bandwidth | Either works; Pages has easier custom-domain + edge |
| Frontend hosting (alt) | Vercel Hobby | 100GB bw/mo, static only | Fine only if you never touch Vercel Functions/Cron; no commercial use on Hobby either |
| Edge KV/cache (optional) | Cloudflare Workers KV | 1GB, 100K reads/1K writes per day | Only if JSON-in-git gets clunky |
| Edge DB (optional) | Cloudflare D1 | 5GB, 5M reads/100K writes per day | Only if you outgrow flat JSON |
| Object storage (optional) | Cloudflare R2 | 10GB storage, 1M ops/mo | For historical OHLCV archive once the repo gets heavy |
| Charts | `lightweight-charts` (TradingView's OSS lib, MIT) | Free, self-hosted | Different product from tradingview.com |
| ~~TradingView alerts/webhook~~ | — | **Not free** — needs Essential $14.95/mo+ | Free plan = 3 price alerts, 0 webhooks. Use Telegram bot instead |
| Notifications | Telegram Bot API | Free, no practical cap for personal use | Same pattern you already run for EvolveAgent/Panda Cyber |
| External cron backup | cron-job.org / UptimeRobot | Free, ping every 5 min | Only if you want tighter-than-GH-Actions scheduling |
| User accounts/watchlist (later) | Supabase free | 500MB Postgres, pauses after ~1wk idle | Skip for v1 |
| Always-on alt to GH Actions | Oracle Cloud Free / GCP e2-micro Free | Free forever, small instance | Only if you want sub-5-min intraday refresh — you already run Oracle for OpenClaw |
| Domain | najibtrader.my.id (already owned) | — | CNAME to Pages, no new purchase needed |

## 6. Build phases — checkpoint after each, don't skip ahead
- **Phase 0 — skeleton:** repo + this AGENTS.md at root + one GitHub Action fetching 5 tickers (BBCA.JK, BBRI.JK, TLKM.JK, AAPL, MSFT), RSI/MACD/BB only, JSON out, committed. Confirm the loop works end-to-end before scaling. Verify current `yfinance`/`pandas-ta` syntax via docs first — these shift.
- **Phase 1 — pilot + full engine:** LQ45 + S&P 500, full §3 scoring + §4 backtest, frontend live on the JSON. First usable version.
- **Phase 2 — scale:** full IHSG (~950) + Russell additions, batching/rate-limit handling, Action-failure alerting to Telegram.
- **Phase 3 — polish:** Telegram push bot, per-ticker detail page + chart, mobile pass, disclaimer footer (§7).

## 7. Non-negotiables
- Every page carries a visible disclaimer: algorithmic technical signals, not financial advice, past performance ≠ future results.
- No hardcoded/fabricated accuracy claims anywhere — code, copy, or commit messages. Only §4's live numbers.
- $0/month is the hard budget. If a task needs a paid tier, stop and flag it instead of assuming an upgrade.
- Data-source failures log loudly — a silent Yahoo throttle must never produce stale signals that look live.
