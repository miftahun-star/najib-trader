"""
backtest.py — Vectorized backtesting of signal logic on historical data.
Computes win rate, avg R-multiple, max drawdown, sample size.
Segmented by market and timeframe.
"""

import logging
from datetime import datetime

import numpy as np
import pandas as pd

from engine.indicators import compute_all_indicators
from engine.scoring import compute_score
from engine.trade_levels import SL_ATR_MULTIPLIER

logger = logging.getLogger(__name__)


def run_backtest(df: pd.DataFrame, ticker: str, market: str, timeframe: str) -> dict:
    """
    Replay signal logic on historical data for a single ticker+timeframe.
    Walks through the data, generates signals, and tracks outcomes.
    Returns backtest statistics.
    """
    results = {
        "ticker": ticker,
        "market": market,
        "timeframe": timeframe,
        "total_trades": 0,
        "wins": 0,
        "losses": 0,
        "win_rate": 0.0,
        "avg_r_multiple": 0.0,
        "max_drawdown": 0.0,
        "r_multiples": [],
        "last_updated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    if df is None or len(df) < 200:
        logger.info(f"Insufficient data for backtest: {ticker} {timeframe} ({len(df) if df is not None else 0} bars)")
        return results

    try:
        trades = []
        lookback = 200  # Need at least 200 bars for MA200

        # Walk forward through data, generating signals at each bar
        for i in range(lookback, len(df) - 20, 5):  # Step by 5 to reduce computation
            window = df.iloc[:i + 1].copy()
            indicators = compute_all_indicators(window)

            if not indicators:
                continue

            score_result = compute_score(indicators)
            signal = score_result["signal"]

            if signal not in ("BOTTOM", "PEAK"):
                continue

            entry_price = df["Close"].iloc[i]
            atr = indicators.get("atr", 0)
            if atr <= 0 or np.isnan(atr):
                continue

            # Simulate trade forward
            trade_result = _simulate_trade(
                df=df,
                entry_idx=i,
                entry_price=entry_price,
                signal=signal,
                atr=atr,
            )

            if trade_result:
                trades.append(trade_result)

        # Compute statistics
        if trades:
            r_multiples = [t["r_multiple"] for t in trades]
            wins = [r for r in r_multiples if r > 0]
            losses = [r for r in r_multiples if r <= 0]

            results["total_trades"] = len(trades)
            results["wins"] = len(wins)
            results["losses"] = len(losses)
            results["win_rate"] = round(len(wins) / len(trades) * 100, 1) if trades else 0
            results["avg_r_multiple"] = round(np.mean(r_multiples), 2) if r_multiples else 0
            results["max_drawdown"] = round(_compute_max_drawdown(trades), 2)
            results["r_multiples"] = [round(r, 2) for r in r_multiples[-50:]]  # Keep last 50

        logger.info(
            f"Backtest {ticker} {timeframe}: {results['total_trades']} trades, "
            f"WR={results['win_rate']}%, avgR={results['avg_r_multiple']}"
        )

    except Exception as e:
        logger.error(f"Backtest error for {ticker} {timeframe}: {e}", exc_info=True)

    return results


def _simulate_trade(
    df: pd.DataFrame,
    entry_idx: int,
    entry_price: float,
    signal: str,
    atr: float,
    max_bars: int = 20,
) -> dict:
    """
    Simulate a trade forward from entry, checking SL/TP hit.
    Returns trade result with R-multiple.
    """
    risk = SL_ATR_MULTIPLIER * atr

    if signal == "BOTTOM":
        sl = entry_price - risk
        tp1 = entry_price + risk
        tp2 = entry_price + 2 * risk

        for j in range(1, min(max_bars, len(df) - entry_idx)):
            bar = df.iloc[entry_idx + j]

            # Check SL hit first (conservative)
            if bar["Low"] <= sl:
                return {"r_multiple": -1.0, "outcome": "SL"}

            # Check TP1 hit
            if bar["High"] >= tp1:
                return {"r_multiple": 1.0, "outcome": "TP1"}

        # If neither hit, mark-to-market at last bar
        last_price = df["Close"].iloc[min(entry_idx + max_bars, len(df) - 1)]
        r = (last_price - entry_price) / risk if risk > 0 else 0
        return {"r_multiple": round(r, 2), "outcome": "TIMEOUT"}

    elif signal == "PEAK":
        sl = entry_price + risk
        tp1 = entry_price - risk
        tp2 = entry_price - 2 * risk

        for j in range(1, min(max_bars, len(df) - entry_idx)):
            bar = df.iloc[entry_idx + j]

            if bar["High"] >= sl:
                return {"r_multiple": -1.0, "outcome": "SL"}

            if bar["Low"] <= tp1:
                return {"r_multiple": 1.0, "outcome": "TP1"}

        last_price = df["Close"].iloc[min(entry_idx + max_bars, len(df) - 1)]
        r = (entry_price - last_price) / risk if risk > 0 else 0
        return {"r_multiple": round(r, 2), "outcome": "TIMEOUT"}

    return None


def _compute_max_drawdown(trades: list) -> float:
    """Compute maximum drawdown from a sequence of trades."""
    if not trades:
        return 0.0

    equity = [0.0]
    for t in trades:
        equity.append(equity[-1] + t["r_multiple"])

    peak = equity[0]
    max_dd = 0.0
    for e in equity:
        if e > peak:
            peak = e
        dd = peak - e
        if dd > max_dd:
            max_dd = dd

    return max_dd


def aggregate_backtest(all_results: list) -> dict:
    """
    Aggregate individual backtest results into market-level and overall stats.
    """
    output = {
        "last_updated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "overall": {"win_rate": 0, "avg_r": 0, "max_dd": 0, "n_trades": 0},
        "markets": {
            "IHSG": {"win_rate": 0, "avg_r": 0, "max_dd": 0, "n_trades": 0, "by_timeframe": {}},
            "US": {"win_rate": 0, "avg_r": 0, "max_dd": 0, "n_trades": 0, "by_timeframe": {}},
        },
    }

    all_trades = 0
    all_wins = 0
    all_r = []
    all_dd = []

    for market_key in ["IHSG", "US"]:
        market_results = [r for r in all_results if r.get("market") == market_key]
        m_trades = sum(r["total_trades"] for r in market_results)
        m_wins = sum(r["wins"] for r in market_results)
        m_r = []
        m_dd = []

        for r in market_results:
            m_r.extend(r.get("r_multiples", []))
            m_dd.append(r.get("max_drawdown", 0))

            tf = r.get("timeframe", "daily")
            output["markets"][market_key]["by_timeframe"][tf] = {
                "win_rate": r["win_rate"],
                "avg_r": r["avg_r_multiple"],
                "max_dd": r["max_drawdown"],
                "n_trades": r["total_trades"],
            }

        output["markets"][market_key]["win_rate"] = round(m_wins / m_trades * 100, 1) if m_trades > 0 else 0
        output["markets"][market_key]["avg_r"] = round(np.mean(m_r), 2) if m_r else 0
        output["markets"][market_key]["max_dd"] = round(max(m_dd), 2) if m_dd else 0
        output["markets"][market_key]["n_trades"] = m_trades

        all_trades += m_trades
        all_wins += m_wins
        all_r.extend(m_r)
        all_dd.extend(m_dd)

    output["overall"]["win_rate"] = round(all_wins / all_trades * 100, 1) if all_trades > 0 else 0
    output["overall"]["avg_r"] = round(np.mean(all_r), 2) if all_r else 0
    output["overall"]["max_dd"] = round(max(all_dd), 2) if all_dd else 0
    output["overall"]["n_trades"] = all_trades

    return output
