"""
indicators.py — Full technical indicator computation per §3.1.
Pure pandas/numpy implementation — no external TA library dependency.
Computes RSI, Stochastic, MACD, Bollinger Bands, ATR, volume analysis,
moving averages, divergence detection, candle patterns, S/R levels, and Fib zones.
Supports precomputed columns to accelerate backtesting walk-forward.
"""

import logging
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# === Core TA functions (pure pandas/numpy) ===

def _rsi(series: pd.Series, length: int = 14) -> pd.Series:
    """Relative Strength Index."""
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1/length, min_periods=length).mean()
    avg_loss = loss.ewm(alpha=1/length, min_periods=length).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _stochastic(high: pd.Series, low: pd.Series, close: pd.Series,
                k_period: int = 14, d_period: int = 3, smooth_k: int = 3) -> pd.DataFrame:
    """Stochastic Oscillator (%K, %D)."""
    lowest_low = low.rolling(k_period).min()
    highest_high = high.rolling(k_period).max()
    raw_k = 100 * (close - lowest_low) / (highest_high - lowest_low).replace(0, np.nan)
    k = raw_k.rolling(smooth_k).mean()
    d = k.rolling(d_period).mean()
    return pd.DataFrame({"stoch_k": k, "stoch_d": d})


def _macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """MACD (Moving Average Convergence Divergence)."""
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return pd.DataFrame({"macd": macd_line, "macd_signal": signal_line, "macd_hist": histogram})


def _bbands(series: pd.Series, length: int = 20, std: float = 2.0) -> pd.DataFrame:
    """Bollinger Bands."""
    mid = series.rolling(length).mean()
    stdev = series.rolling(length).std()
    upper = mid + std * stdev
    lower = mid - std * stdev
    return pd.DataFrame({"bb_upper": upper, "bb_mid": mid, "bb_lower": lower})


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14) -> pd.Series:
    """Average True Range."""
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.ewm(alpha=1/length, min_periods=length).mean()


def _sma(series: pd.Series, length: int) -> pd.Series:
    """Simple Moving Average."""
    return series.rolling(length).mean()


# === Main computation ===

def compute_all_indicators(df: pd.DataFrame) -> dict:
    """
    Compute all indicators on a DataFrame with OHLCV columns.
    Returns a dict of indicator values for the latest bar.
    """
    if df is None or len(df) < 30:
        return {}

    result = {}

    try:
        df = df.copy()

        # === Core indicators (support precomputed columns for speed) ===
        
        # RSI(14)
        if "rsi" not in df.columns:
            df["rsi"] = _rsi(df["Close"], length=14)
        result["rsi"] = _safe_last(df["rsi"])

        # Stochastic(14,3,3)
        if "stoch_k" not in df.columns or "stoch_d" not in df.columns:
            stoch = _stochastic(df["High"], df["Low"], df["Close"], k_period=14, d_period=3, smooth_k=3)
            df["stoch_k"] = stoch["stoch_k"]
            df["stoch_d"] = stoch["stoch_d"]
        result["stoch_k"] = _safe_last(df["stoch_k"])
        result["stoch_d"] = _safe_last(df["stoch_d"])

        # MACD(12,26,9)
        if "macd" not in df.columns or "macd_signal" not in df.columns or "macd_hist" not in df.columns:
            macd = _macd(df["Close"], fast=12, slow=26, signal=9)
            df["macd"] = macd["macd"]
            df["macd_signal"] = macd["macd_signal"]
            df["macd_hist"] = macd["macd_hist"]
        result["macd"] = _safe_last(df["macd"])
        result["macd_signal"] = _safe_last(df["macd_signal"])
        result["macd_hist"] = _safe_last(df["macd_hist"])

        # Bollinger Bands(20,2)
        if "bb_upper" not in df.columns or "bb_mid" not in df.columns or "bb_lower" not in df.columns:
            bb = _bbands(df["Close"], length=20, std=2)
            df["bb_upper"] = bb["bb_upper"]
            df["bb_mid"] = bb["bb_mid"]
            df["bb_lower"] = bb["bb_lower"]
        result["bb_upper"] = _safe_last(df["bb_upper"])
        result["bb_mid"] = _safe_last(df["bb_mid"])
        result["bb_lower"] = _safe_last(df["bb_lower"])

        # ATR(14)
        if "atr" not in df.columns:
            df["atr"] = _atr(df["High"], df["Low"], df["Close"], length=14)
        result["atr"] = _safe_last(df["atr"])

        # MA50 and MA200
        if "ma50" not in df.columns:
            df["ma50"] = _sma(df["Close"], length=50)
        if "ma200" not in df.columns:
            df["ma200"] = _sma(df["Close"], length=200) if len(df) >= 200 else pd.Series([np.nan] * len(df), index=df.index)
        result["ma50"] = _safe_last(df["ma50"])
        result["ma200"] = _safe_last(df["ma200"])
        result["price"] = _safe_last(df["Close"])

        # Price vs MA position
        result["above_ma50"] = bool(result["price"] > result["ma50"]) if not np.isnan(result["ma50"]) else None
        result["above_ma200"] = bool(result["price"] > result["ma200"]) if not np.isnan(result["ma200"]) else None

        # Volume vs 20-period average
        if "vol_avg20" not in df.columns:
            df["vol_avg20"] = df["Volume"].rolling(20).mean()
        result["volume"] = _safe_last(df["Volume"])
        result["vol_avg20"] = _safe_last(df["vol_avg20"])
        result["vol_ratio"] = round(result["volume"] / result["vol_avg20"], 2) if result["vol_avg20"] > 0 else 1.0

        # === Advanced indicators ===
        # Divergence detection
        result["bullish_divergence"] = detect_divergence(df, "bullish")
        result["bearish_divergence"] = detect_divergence(df, "bearish")

        # Candle patterns
        result["candle_pattern"] = detect_candle_patterns(df)

        # Support/Resistance levels
        sr_levels = detect_support_resistance(df)
        result["support_levels"] = sr_levels["support"]
        result["resistance_levels"] = sr_levels["resistance"]
        result["near_support"] = sr_levels["near_support"]
        result["near_resistance"] = sr_levels["near_resistance"]

        # Fibonacci zones
        fib = compute_fibonacci(df)
        result["fib_levels"] = fib["levels"]
        result["in_fib_zone"] = fib["in_zone"]
        result["fib_zone_type"] = fib["zone_type"]

        # BB touch detection
        result["bb_touch"] = detect_bb_touch(df)

        # Volume climax
        result["volume_climax"] = bool(result["vol_ratio"] >= 2.0)

    except Exception as e:
        logger.error(f"Error computing indicators: {e}", exc_info=True)

    return result


def _safe_last(series: pd.Series) -> float:
    """Get last non-NaN value from a series."""
    if series is None or series.empty:
        return np.nan
    val = series.dropna().iloc[-1] if not series.dropna().empty else np.nan
    return round(float(val), 4) if not np.isnan(val) else np.nan


def _find_swing_points(series: pd.Series, order: int = 5) -> tuple:
    """Find swing highs and swing lows in a series."""
    highs = []
    lows = []
    vals = series.dropna().values
    indices = series.dropna().index

    for i in range(order, len(vals) - order):
        if all(vals[i] >= vals[i - j] for j in range(1, order + 1)) and \
           all(vals[i] >= vals[i + j] for j in range(1, order + 1)):
            highs.append((indices[i], vals[i]))

        if all(vals[i] <= vals[i - j] for j in range(1, order + 1)) and \
           all(vals[i] <= vals[i + j] for j in range(1, order + 1)):
            lows.append((indices[i], vals[i]))

    return highs, lows


def detect_divergence(df: pd.DataFrame, div_type: str) -> bool:
    """
    Detect bullish or bearish divergence between price and RSI/MACD.
    Uses last 2 swing points.
    """
    try:
        if "rsi" not in df.columns or df["rsi"].isna().all():
            return False

        price_highs, price_lows = _find_swing_points(df["Close"], order=5)
        rsi_highs, rsi_lows = _find_swing_points(df["rsi"], order=5)

        if div_type == "bullish":
            if len(price_lows) >= 2 and len(rsi_lows) >= 2:
                p1, p2 = price_lows[-2], price_lows[-1]
                r1, r2 = rsi_lows[-2], rsi_lows[-1]
                if p2[1] < p1[1] and r2[1] > r1[1]:
                    return True

        elif div_type == "bearish":
            if len(price_highs) >= 2 and len(rsi_highs) >= 2:
                p1, p2 = price_highs[-2], price_highs[-1]
                r1, r2 = rsi_highs[-2], rsi_highs[-1]
                if p2[1] > p1[1] and r2[1] < r1[1]:
                    return True

    except Exception as e:
        logger.debug(f"Divergence detection error: {e}")

    return False


def detect_candle_patterns(df: pd.DataFrame) -> dict:
    """
    Detect reversal candle patterns on the last 3 bars.
    Returns dict with pattern name and direction.
    """
    patterns = {"name": None, "direction": None}

    try:
        if len(df) < 3:
            return patterns

        c = df.iloc[-1]
        p = df.iloc[-2]
        pp = df.iloc[-3]

        body = abs(c["Close"] - c["Open"])
        upper_wick = c["High"] - max(c["Close"], c["Open"])
        lower_wick = min(c["Close"], c["Open"]) - c["Low"]
        total_range = c["High"] - c["Low"]

        if total_range == 0:
            return patterns

        # Hammer (bullish)
        if lower_wick >= 2 * body and upper_wick <= body * 0.5 and c["Close"] > c["Open"]:
            patterns = {"name": "hammer", "direction": "bullish"}

        # Shooting star (bearish)
        elif upper_wick >= 2 * body and lower_wick <= body * 0.5 and c["Close"] < c["Open"]:
            patterns = {"name": "shooting_star", "direction": "bearish"}

        # Bullish engulfing
        elif (p["Close"] < p["Open"] and
              c["Close"] > c["Open"] and
              c["Open"] <= p["Close"] and
              c["Close"] >= p["Open"]):
            patterns = {"name": "bullish_engulfing", "direction": "bullish"}

        # Bearish engulfing
        elif (p["Close"] > p["Open"] and
              c["Close"] < c["Open"] and
              c["Open"] >= p["Close"] and
              c["Close"] <= p["Open"]):
            patterns = {"name": "bearish_engulfing", "direction": "bearish"}

        # Morning star (3-bar bullish)
        elif (pp["Close"] < pp["Open"] and
              abs(p["Close"] - p["Open"]) < abs(pp["Close"] - pp["Open"]) * 0.3 and
              c["Close"] > c["Open"] and
              c["Close"] > (pp["Open"] + pp["Close"]) / 2):
            patterns = {"name": "morning_star", "direction": "bullish"}

        # Evening star (3-bar bearish)
        elif (pp["Close"] > pp["Open"] and
              abs(p["Close"] - p["Open"]) < abs(pp["Close"] - pp["Open"]) * 0.3 and
              c["Close"] < c["Open"] and
              c["Close"] < (pp["Open"] + pp["Close"]) / 2):
            patterns = {"name": "evening_star", "direction": "bearish"}

    except Exception as e:
        logger.debug(f"Candle pattern detection error: {e}")

    return patterns


def detect_support_resistance(df: pd.DataFrame, lookback: int = 100) -> dict:
    """
    Detect horizontal S/R levels from the last `lookback` bars.
    A level is valid if price touched it ≥2 times within 1×ATR tolerance.
    """
    result = {"support": [], "resistance": [], "near_support": False, "near_resistance": False}

    try:
        data = df.tail(lookback).copy()
        if len(data) < 20 or "atr" not in data.columns:
            return result

        atr = data["atr"].dropna().iloc[-1] if not data["atr"].dropna().empty else 0
        if atr == 0:
            return result

        current_price = data["Close"].iloc[-1]

        _, lows = _find_swing_points(data["Low"], order=3)
        highs, _ = _find_swing_points(data["High"], order=3)

        support_levels = _cluster_levels([l[1] for l in lows], atr)
        resistance_levels = _cluster_levels([h[1] for h in highs], atr)

        support_levels = [l for l in support_levels if l["touches"] >= 2]
        resistance_levels = [l for l in resistance_levels if l["touches"] >= 2]

        result["support"] = [round(l["level"], 2) for l in support_levels[:5]]
        result["resistance"] = [round(l["level"], 2) for l in resistance_levels[:5]]

        for s in result["support"]:
            if abs(current_price - s) <= atr:
                result["near_support"] = True
                break
        for r in result["resistance"]:
            if abs(current_price - r) <= atr:
                result["near_resistance"] = True
                break

    except Exception as e:
        logger.debug(f"S/R detection error: {e}")

    return result


def _cluster_levels(prices: list, tolerance: float) -> list:
    """Cluster nearby price levels and count touches."""
    if not prices:
        return []

    prices = sorted(prices)
    clusters = []
    current_cluster = [prices[0]]

    for p in prices[1:]:
        if p - current_cluster[-1] <= tolerance:
            current_cluster.append(p)
        else:
            clusters.append({
                "level": np.mean(current_cluster),
                "touches": len(current_cluster),
            })
            current_cluster = [p]

    clusters.append({
        "level": np.mean(current_cluster),
        "touches": len(current_cluster),
    })

    return sorted(clusters, key=lambda x: x["touches"], reverse=True)


def compute_fibonacci(df: pd.DataFrame, lookback: int = 100) -> dict:
    """
    Compute Fibonacci retracement levels from recent swing high/low.
    Check if current price is in the 38.2-61.8% retracement zone.
    """
    result = {"levels": {}, "in_zone": False, "zone_type": None}

    try:
        data = df.tail(lookback)
        if len(data) < 20:
            return result

        swing_high = data["High"].max()
        swing_low = data["Low"].min()
        current_price = data["Close"].iloc[-1]
        diff = swing_high - swing_low

        if diff <= 0:
            return result

        levels = {
            "0.0": round(swing_high, 2),
            "23.6": round(swing_high - 0.236 * diff, 2),
            "38.2": round(swing_high - 0.382 * diff, 2),
            "50.0": round(swing_high - 0.500 * diff, 2),
            "61.8": round(swing_high - 0.618 * diff, 2),
            "78.6": round(swing_high - 0.786 * diff, 2),
            "100.0": round(swing_low, 2),
        }
        result["levels"] = levels

        fib_382 = levels["38.2"]
        fib_618 = levels["61.8"]

        if fib_618 <= current_price <= fib_382:
            result["in_zone"] = True
            mid = (swing_high + swing_low) / 2
            if current_price > mid:
                result["zone_type"] = "pullback_in_uptrend"
            else:
                result["zone_type"] = "pullback_in_downtrend"

    except Exception as e:
        logger.debug(f"Fibonacci computation error: {e}")

    return result


def detect_bb_touch(df: pd.DataFrame) -> str:
    """Detect if price is touching/breaching Bollinger Bands."""
    try:
        if "bb_lower" not in df.columns or "bb_upper" not in df.columns:
            return "none"

        close = df["Close"].iloc[-1]
        bb_lower = df["bb_lower"].iloc[-1]
        bb_upper = df["bb_upper"].iloc[-1]

        if np.isnan(bb_lower) or np.isnan(bb_upper):
            return "none"

        if close <= bb_lower:
            return "lower"
        elif close >= bb_upper:
            return "upper"
        else:
            return "none"

    except Exception:
        return "none"
