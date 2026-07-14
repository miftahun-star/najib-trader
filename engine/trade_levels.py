"""
trade_levels.py — ATR-based trade levels per §3.3.
Entry, Stop Loss, Take Profit (TP1/TP2/TP3), Trailing Stop, R:R ratio.
"""

import logging
import numpy as np

logger = logging.getLogger(__name__)

# Configurable parameters (to be tuned via backtest)
SL_ATR_MULTIPLIER = 1.5
TRAIL_K = 2.5  # Chandelier trailing stop multiplier, tuned via backtest (range 2-3)


def compute_trade_levels(signal: str, indicators: dict) -> dict:
    """
    Compute trade levels for a given signal.
    Returns entry, stop loss, TP1/2/3, trailing stop params, and R:R ratio.
    """
    result = {
        "entry": None,
        "stop_loss": None,
        "tp1": None,
        "tp2": None,
        "tp3": None,
        "risk": None,
        "rr_ratio": None,
        "trailing_stop": None,
        "trailing_k": TRAIL_K,
    }

    if signal not in ("BOTTOM", "PEAK"):
        return result

    price = indicators.get("price")
    atr = indicators.get("atr")

    if price is None or atr is None or np.isnan(price) or np.isnan(atr) or atr <= 0:
        logger.warning("Cannot compute trade levels: missing price or ATR")
        return result

    entry = round(price, 2)
    result["entry"] = entry

    if signal == "BOTTOM":
        # Long trade
        sl = round(entry - SL_ATR_MULTIPLIER * atr, 2)
        risk = round(entry - sl, 2)

        tp1 = round(entry + 1 * risk, 2)
        tp2 = round(entry + 2 * risk, 2)
        tp3_default = round(entry + 3 * risk, 2)

        # TP3 = min(3×Risk, nearest resistance/Fib extension)
        tp3 = _adjust_tp3_to_resistance(tp3_default, indicators, "long")

        result.update({
            "stop_loss": sl,
            "risk": risk,
            "tp1": tp1,
            "tp2": tp2,
            "tp3": tp3,
            "rr_ratio": f"1:{round(risk / risk, 1) if risk > 0 else 0} / 1:{round(2 * risk / risk, 1) if risk > 0 else 0} / 1:{round((tp3 - entry) / risk, 1) if risk > 0 else 0}",
            "trailing_stop": round(entry - TRAIL_K * atr, 2),
        })

    elif signal == "PEAK":
        # Short trade
        sl = round(entry + SL_ATR_MULTIPLIER * atr, 2)
        risk = round(sl - entry, 2)

        tp1 = round(entry - 1 * risk, 2)
        tp2 = round(entry - 2 * risk, 2)
        tp3_default = round(entry - 3 * risk, 2)

        tp3 = _adjust_tp3_to_support(tp3_default, indicators, "short")

        result.update({
            "stop_loss": sl,
            "risk": risk,
            "tp1": tp1,
            "tp2": tp2,
            "tp3": tp3,
            "rr_ratio": f"1:{round(risk / risk, 1) if risk > 0 else 0} / 1:{round(2 * risk / risk, 1) if risk > 0 else 0} / 1:{round((entry - tp3) / risk, 1) if risk > 0 else 0}",
            "trailing_stop": round(entry + TRAIL_K * atr, 2),
        })

    return result


def _adjust_tp3_to_resistance(tp3_default: float, indicators: dict, direction: str) -> float:
    """Adjust TP3 to nearest resistance/Fib extension if closer."""
    resistance_levels = indicators.get("resistance_levels", [])
    fib_levels = indicators.get("fib_levels", {})
    entry = indicators.get("price", tp3_default)

    candidates = [tp3_default]

    # Check resistance levels above entry
    for r in resistance_levels:
        if r > entry:
            candidates.append(r)

    # Check Fib extension levels
    for key, val in fib_levels.items():
        if isinstance(val, (int, float)) and val > entry:
            candidates.append(val)

    # Pick the closest to entry that is still profitable
    valid = [c for c in candidates if c > entry]
    return round(min(valid), 2) if valid else tp3_default


def _adjust_tp3_to_support(tp3_default: float, indicators: dict, direction: str) -> float:
    """Adjust TP3 to nearest support/Fib level if closer."""
    support_levels = indicators.get("support_levels", [])
    fib_levels = indicators.get("fib_levels", {})
    entry = indicators.get("price", tp3_default)

    candidates = [tp3_default]

    for s in support_levels:
        if s < entry:
            candidates.append(s)

    for key, val in fib_levels.items():
        if isinstance(val, (int, float)) and val < entry:
            candidates.append(val)

    valid = [c for c in candidates if c < entry]
    return round(max(valid), 2) if valid else tp3_default


def compute_trailing_stop(
    entry: float,
    highest_since_entry: float,
    lowest_since_entry: float,
    atr: float,
    signal: str,
    k: float = TRAIL_K,
) -> float:
    """
    Chandelier trailing stop — ratchets toward profit only, never loosens.
    Long: trail = highest_high - k * ATR
    Short: trail = lowest_low + k * ATR
    """
    if signal == "BOTTOM":
        trail = round(highest_since_entry - k * atr, 2)
        # Never loosen below entry - SL distance
        minimum = round(entry - SL_ATR_MULTIPLIER * atr, 2)
        return max(trail, minimum)
    elif signal == "PEAK":
        trail = round(lowest_since_entry + k * atr, 2)
        maximum = round(entry + SL_ATR_MULTIPLIER * atr, 2)
        return min(trail, maximum)
    return 0
