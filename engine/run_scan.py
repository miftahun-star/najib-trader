"""
run_scan.py — Main orchestrator for the signal scanner.
Fetches data, computes indicators/scores/trade levels per timeframe,
generates yearly trend overlay, runs backtest, outputs JSON.
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.fetch_data import (
    fetch_all_tickers,
    resample_to_weekly,
    resample_to_monthly,
    MARKET_MAP,
    ALL_TICKERS,
)
from engine.indicators import compute_all_indicators
from engine.scoring import compute_score
from engine.trade_levels import compute_trade_levels
from engine.backtest import run_backtest, aggregate_backtest

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Output directories
DATA_DIR = Path(__file__).parent.parent / "data"
SIGNALS_DIR = DATA_DIR / "signals"


class NumpyEncoder(json.JSONEncoder):
    """JSON encoder that handles numpy types."""
    def default(self, obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return round(float(obj), 4)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, (np.bool_,)):
            return bool(obj)
        if pd.isna(obj):
            return None
        return super().default(obj)


def compute_yearly_trend(daily_df: pd.DataFrame) -> dict:
    """
    Compute yearly trend overlay — NOT a reversal signal.
    Shows price vs weekly MA200 and higher-high/higher-low structure.
    """
    trend = {
        "bias": "neutral",
        "ma200_position": None,
        "structure": None,
        "description": "Long-term trend bias — not a reversal call",
    }

    try:
        if daily_df is None or len(daily_df) < 200:
            return trend

        weekly = resample_to_weekly(daily_df)
        if len(weekly) < 50:
            return trend

        # Weekly MA200 (pure pandas)
        ma_len = min(200, len(weekly) - 1)
        ma200 = weekly["Close"].rolling(ma_len).mean()
        if ma200 is not None and not ma200.dropna().empty:
            current_price = weekly["Close"].iloc[-1]
            ma200_val = ma200.dropna().iloc[-1]
            trend["ma200_position"] = "above" if current_price > ma200_val else "below"

        # Higher-high / higher-low structure (last 4 swing points)
        closes = weekly["Close"].values
        if len(closes) >= 20:
            # Simple structure: compare last 4 local extremes
            highs = []
            lows = []
            for i in range(5, len(closes) - 5):
                if closes[i] == max(closes[i-5:i+6]):
                    highs.append(closes[i])
                if closes[i] == min(closes[i-5:i+6]):
                    lows.append(closes[i])

            if len(highs) >= 2 and len(lows) >= 2:
                hh = highs[-1] > highs[-2]  # Higher high
                hl = lows[-1] > lows[-2]    # Higher low
                lh = highs[-1] < highs[-2]  # Lower high
                ll = lows[-1] < lows[-2]    # Lower low

                if hh and hl:
                    trend["structure"] = "uptrend (HH+HL)"
                    trend["bias"] = "bullish"
                elif lh and ll:
                    trend["structure"] = "downtrend (LH+LL)"
                    trend["bias"] = "bearish"
                elif hh and ll:
                    trend["structure"] = "expanding (HH+LL)"
                    trend["bias"] = "volatile"
                elif lh and hl:
                    trend["structure"] = "contracting (LH+HL)"
                    trend["bias"] = "consolidating"
                else:
                    trend["structure"] = "mixed"
                    trend["bias"] = "neutral"

    except Exception as e:
        logger.error(f"Yearly trend computation error: {e}")

    return trend


def process_ticker(ticker: str, daily_df: pd.DataFrame) -> dict:
    """Process a single ticker across all timeframes."""
    market = MARKET_MAP.get(ticker, "UNKNOWN")
    stale = daily_df.attrs.get("stale", False)

    ticker_data = {
        "ticker": ticker,
        "market": market,
        "last_updated": datetime.now(tz=__import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "data_stale": stale,
        "timeframes": {},
        "yearly_trend": {},
    }

    if stale:
        logger.warning(f"⚠ {ticker}: Using STALE data — last bar: {daily_df.attrs.get('last_bar', 'unknown')}")

    # Process each timeframe independently
    timeframe_dfs = {
        "daily": daily_df,
        "weekly": resample_to_weekly(daily_df),
        "monthly": resample_to_monthly(daily_df),
    }

    for tf_name, tf_df in timeframe_dfs.items():
        if tf_df is None or len(tf_df) < 30:
            logger.info(f"Skipping {ticker} {tf_name}: insufficient data ({len(tf_df) if tf_df is not None else 0} bars)")
            continue

        try:
            # 1. Compute indicators
            indicators = compute_all_indicators(tf_df)

            # 2. Compute score
            score_result = compute_score(indicators)

            # 3. Compute trade levels
            trade_levels = compute_trade_levels(score_result["signal"], indicators)

            # 4. Build timeframe output
            ticker_data["timeframes"][tf_name] = {
                "signal": score_result["signal"],
                "score": score_result["score"],
                "reason": score_result["reason"],
                "components": score_result["components"],
                "indicators": {
                    "rsi": indicators.get("rsi"),
                    "stoch_k": indicators.get("stoch_k"),
                    "stoch_d": indicators.get("stoch_d"),
                    "macd": indicators.get("macd"),
                    "macd_signal": indicators.get("macd_signal"),
                    "macd_hist": indicators.get("macd_hist"),
                    "bb_upper": indicators.get("bb_upper"),
                    "bb_mid": indicators.get("bb_mid"),
                    "bb_lower": indicators.get("bb_lower"),
                    "atr": indicators.get("atr"),
                    "ma50": indicators.get("ma50"),
                    "ma200": indicators.get("ma200"),
                    "price": indicators.get("price"),
                    "vol_ratio": indicators.get("vol_ratio"),
                    "above_ma50": indicators.get("above_ma50"),
                    "above_ma200": indicators.get("above_ma200"),
                },
                "patterns": {
                    "candle": indicators.get("candle_pattern"),
                    "bullish_divergence": indicators.get("bullish_divergence"),
                    "bearish_divergence": indicators.get("bearish_divergence"),
                    "bb_touch": indicators.get("bb_touch"),
                    "volume_climax": indicators.get("volume_climax"),
                    "near_support": indicators.get("near_support"),
                    "near_resistance": indicators.get("near_resistance"),
                    "in_fib_zone": indicators.get("in_fib_zone"),
                },
                "trade_levels": trade_levels,
                "support_levels": indicators.get("support_levels", []),
                "resistance_levels": indicators.get("resistance_levels", []),
                "fib_levels": indicators.get("fib_levels", {}),
            }

        except Exception as e:
            logger.error(f"Error processing {ticker} {tf_name}: {e}", exc_info=True)

    # Yearly trend overlay (not a reversal signal)
    ticker_data["yearly_trend"] = compute_yearly_trend(daily_df)

    return ticker_data


def run():
    """Main scan execution."""
    logger.info("=" * 60)
    logger.info(f"SIGNAL SCAN STARTED — {datetime.now(tz=__import__("datetime").timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    logger.info("=" * 60)

    # Ensure output dirs exist
    SIGNALS_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Fetch all data
    logger.info("Step 1: Fetching OHLCV data...")
    daily_data = fetch_all_tickers()

    if not daily_data:
        logger.error("CRITICAL: No data fetched for any ticker. Aborting scan.")
        sys.exit(1)

    # 2. Process each ticker
    logger.info("Step 2: Processing tickers...")
    all_signals = []
    all_backtest_results = []

    for ticker, daily_df in daily_data.items():
        logger.info(f"Processing {ticker}...")
        ticker_result = process_ticker(ticker, daily_df)
        all_signals.append(ticker_result)

        # Write individual ticker JSON
        safe_name = ticker.replace(".", "_")
        ticker_file = SIGNALS_DIR / f"{safe_name}.json"
        with open(ticker_file, "w") as f:
            json.dump(ticker_result, f, cls=NumpyEncoder, indent=2)
        logger.info(f"  → Written: {ticker_file.name}")

        # 3. Run backtest per timeframe
        for tf_name, tf_df in [("daily", daily_df), ("weekly", resample_to_weekly(daily_df)), ("monthly", resample_to_monthly(daily_df))]:
            if tf_df is not None and len(tf_df) >= 200:
                market = MARKET_MAP.get(ticker, "UNKNOWN")
                bt = run_backtest(tf_df, ticker, market, tf_name)
                all_backtest_results.append(bt)

    # 4. Write index.json (summary of all tickers)
    index_data = {
        "last_updated": datetime.now(tz=__import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ticker_count": len(all_signals),
        "tickers": [],
    }

    for sig in all_signals:
        daily_tf = sig.get("timeframes", {}).get("daily", {})
        index_data["tickers"].append({
            "ticker": sig["ticker"],
            "market": sig["market"],
            "signal": daily_tf.get("signal", "HOLD"),
            "score": daily_tf.get("score", 50),
            "price": daily_tf.get("indicators", {}).get("price"),
            "data_stale": sig.get("data_stale", False),
        })

    index_file = SIGNALS_DIR / "index.json"
    with open(index_file, "w") as f:
        json.dump(index_data, f, cls=NumpyEncoder, indent=2)
    logger.info(f"Written: {index_file.name}")

    # 5. Aggregate and write backtest
    logger.info("Step 3: Aggregating backtest results...")
    backtest_output = aggregate_backtest(all_backtest_results)
    backtest_file = DATA_DIR / "backtest.json"
    with open(backtest_file, "w") as f:
        json.dump(backtest_output, f, cls=NumpyEncoder, indent=2)
    logger.info(f"Written: {backtest_file.name}")

    # Summary
    logger.info("=" * 60)
    logger.info("SCAN COMPLETE")
    logger.info(f"  Tickers processed: {len(all_signals)}")

    signal_counts = {}
    for sig in all_signals:
        daily_signal = sig.get("timeframes", {}).get("daily", {}).get("signal", "HOLD")
        signal_counts[daily_signal] = signal_counts.get(daily_signal, 0) + 1
    for s, c in signal_counts.items():
        logger.info(f"  {s}: {c}")

    if backtest_output["overall"]["n_trades"] > 0:
        logger.info(f"  Backtest: WR={backtest_output['overall']['win_rate']}%, "
                    f"avgR={backtest_output['overall']['avg_r']}, "
                    f"n={backtest_output['overall']['n_trades']}")
    logger.info("=" * 60)


if __name__ == "__main__":
    run()
