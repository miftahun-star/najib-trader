"""
scoring.py — Composite signal scoring (0-100) per §3.2.
Weighted confluence of multiple indicator groups.
"""

import logging
import numpy as np

logger = logging.getLogger(__name__)

# Scoring weights (starting point — to be re-tuned via backtest)
WEIGHTS = {
    "rsi_stoch": 0.20,      # RSI/Stochastic extreme
    "divergence": 0.25,      # Bullish/bearish divergence
    "candle_pattern": 0.15,  # Reversal candle patterns
    "bb_touch": 0.15,        # Bollinger Band touch
    "volume_climax": 0.10,   # Volume climax
    "sr_fib": 0.15,          # S/R or Fibonacci confluence
}

# Signal thresholds
BOTTOM_THRESHOLD = 70  # ≥70 at range low → BOTTOM (buy)
PEAK_THRESHOLD = 30    # ≤30 at range high → PEAK (sell)
HOLD_LOW = 40
HOLD_HIGH = 60


def compute_score(indicators: dict) -> dict:
    """
    Compute composite score and classify signal.
    Returns dict with score, signal, component scores, and reasoning.
    """
    if not indicators:
        return {"score": 50, "signal": "HOLD", "components": {}, "reason": "No indicators available"}

    components = {}
    reasons = []

    # === 1. RSI/Stochastic extreme (0-100 sub-score) ===
    rsi_score = _score_rsi_stoch(indicators)
    components["rsi_stoch"] = rsi_score

    # === 2. Divergence (0-100 sub-score) ===
    div_score = _score_divergence(indicators)
    components["divergence"] = div_score

    # === 3. Candle pattern (0-100 sub-score) ===
    candle_score = _score_candle(indicators)
    components["candle_pattern"] = candle_score

    # === 4. Bollinger Band touch (0-100 sub-score) ===
    bb_score = _score_bb(indicators)
    components["bb_touch"] = bb_score

    # === 5. Volume climax (0-100 sub-score) ===
    vol_score = _score_volume(indicators)
    components["volume_climax"] = vol_score

    # === 6. S/R or Fibonacci confluence (0-100 sub-score) ===
    sr_fib_score = _score_sr_fib(indicators)
    components["sr_fib"] = sr_fib_score

    # Weighted composite
    composite = sum(
        components[k] * WEIGHTS[k] for k in WEIGHTS if k in components
    )
    composite = round(min(100, max(0, composite)), 1)

    # Determine direction bias (bottom vs peak scoring)
    bottom_bias = _is_range_low(indicators)
    peak_bias = _is_range_high(indicators)

    # Classify signal
    if composite >= BOTTOM_THRESHOLD and bottom_bias:
        signal = "BOTTOM"
        reasons.append(f"High confluence score ({composite}) at range low")
    elif composite <= PEAK_THRESHOLD and peak_bias:
        signal = "PEAK"
        reasons.append(f"Low confluence score ({composite}) at range high")
    elif HOLD_LOW <= composite <= HOLD_HIGH:
        signal = "HOLD"
        reasons.append(f"Neutral zone ({composite})")
    else:
        signal = "WATCH"
        if composite > HOLD_HIGH:
            reasons.append(f"Elevated score ({composite}) but not at confirmed range low")
        else:
            reasons.append(f"Depressed score ({composite}) but not at confirmed range high")

    # Build reason string
    if components.get("divergence", 50) > 70:
        reasons.append("Bullish divergence detected")
    elif components.get("divergence", 50) < 30:
        reasons.append("Bearish divergence detected")

    candle = indicators.get("candle_pattern", {})
    if candle.get("name"):
        reasons.append(f"Candle: {candle['name']} ({candle.get('direction', 'neutral')})")

    return {
        "score": composite,
        "signal": signal,
        "components": {k: round(v, 1) for k, v in components.items()},
        "reason": " | ".join(reasons),
        "weights": WEIGHTS,
    }


def _score_rsi_stoch(ind: dict) -> float:
    """Score RSI/Stochastic extremes. High score = oversold (bottom), low = overbought (peak)."""
    score = 50.0
    rsi = ind.get("rsi", 50)
    stoch_k = ind.get("stoch_k", 50)

    if not np.isnan(rsi):
        if rsi <= 30:
            score += 25 * (1 - rsi / 30)  # More oversold = higher score
        elif rsi >= 70:
            score -= 25 * ((rsi - 70) / 30)  # More overbought = lower score

    if not np.isnan(stoch_k):
        if stoch_k <= 20:
            score += 25 * (1 - stoch_k / 20)
        elif stoch_k >= 80:
            score -= 25 * ((stoch_k - 80) / 20)

    return min(100, max(0, score))


def _score_divergence(ind: dict) -> float:
    """Score divergence signals."""
    if ind.get("bullish_divergence"):
        return 90.0
    elif ind.get("bearish_divergence"):
        return 10.0
    return 50.0


def _score_candle(ind: dict) -> float:
    """Score candle patterns."""
    pattern = ind.get("candle_pattern", {})
    if not pattern or not pattern.get("name"):
        return 50.0

    direction = pattern.get("direction", "neutral")
    name = pattern.get("name", "")

    # Strong patterns score higher
    strong_patterns = ["morning_star", "evening_star", "bullish_engulfing", "bearish_engulfing"]
    weight = 90.0 if name in strong_patterns else 75.0

    if direction == "bullish":
        return weight
    elif direction == "bearish":
        return 100 - weight
    return 50.0


def _score_bb(ind: dict) -> float:
    """Score Bollinger Band touch."""
    bb_touch = ind.get("bb_touch", "none")
    if bb_touch == "lower":
        return 85.0  # Price at lower BB = potential bottom
    elif bb_touch == "upper":
        return 15.0  # Price at upper BB = potential peak
    return 50.0


def _score_volume(ind: dict) -> float:
    """Score volume climax."""
    vol_ratio = ind.get("vol_ratio", 1.0)
    if ind.get("volume_climax"):
        # Volume climax can signal exhaustion (reversal) in context
        return 80.0
    elif vol_ratio >= 1.5:
        return 65.0
    return 50.0


def _score_sr_fib(ind: dict) -> float:
    """Score support/resistance and Fibonacci confluence."""
    score = 50.0

    if ind.get("near_support"):
        score += 20.0
    if ind.get("near_resistance"):
        score -= 20.0

    if ind.get("in_fib_zone"):
        zone_type = ind.get("fib_zone_type", "")
        if "uptrend" in str(zone_type):
            score += 15.0  # Pullback in uptrend to Fib zone = buy opportunity
        elif "downtrend" in str(zone_type):
            score -= 15.0

    return min(100, max(0, score))


def _is_range_low(ind: dict) -> bool:
    """Check if price is at the low end of its range."""
    rsi = ind.get("rsi", 50)
    bb_touch = ind.get("bb_touch", "none")
    near_support = ind.get("near_support", False)

    conditions = 0
    if not np.isnan(rsi) and rsi < 40:
        conditions += 1
    if bb_touch == "lower":
        conditions += 1
    if near_support:
        conditions += 1

    return conditions >= 1


def _is_range_high(ind: dict) -> bool:
    """Check if price is at the high end of its range."""
    rsi = ind.get("rsi", 50)
    bb_touch = ind.get("bb_touch", "none")
    near_resistance = ind.get("near_resistance", False)

    conditions = 0
    if not np.isnan(rsi) and rsi > 60:
        conditions += 1
    if bb_touch == "upper":
        conditions += 1
    if near_resistance:
        conditions += 1

    return conditions >= 1
