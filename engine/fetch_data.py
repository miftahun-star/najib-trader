"""
fetch_data.py — OHLCV data fetcher with retry logic and staleness detection.
Supports yfinance as primary source with throttle-aware error handling.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

# Phase 0 tickers
PHASE0_IHSG = ["BBCA.JK", "BBRI.JK", "TLKM.JK"]
PHASE0_US = ["AAPL", "MSFT"]
ALL_TICKERS = PHASE0_IHSG + PHASE0_US

MARKET_MAP = {}
for t in PHASE0_IHSG:
    MARKET_MAP[t] = "IHSG"
for t in PHASE0_US:
    MARKET_MAP[t] = "US"

MAX_RETRIES = 3
RETRY_DELAY_BASE = 5  # seconds, exponential backoff
BATCH_DELAY = 1.5  # seconds between tickers to avoid throttle


def fetch_ohlcv(
    ticker: str,
    period: str = "2y",
    interval: str = "1d",
    retries: int = MAX_RETRIES,
) -> Optional[pd.DataFrame]:
    """
    Fetch OHLCV data for a single ticker from yfinance.
    Returns DataFrame with columns: Open, High, Low, Close, Volume, or None on failure.
    """
    for attempt in range(1, retries + 1):
        try:
            logger.info(f"Fetching {ticker} (attempt {attempt}/{retries}, interval={interval}, period={period})")
            tkr = yf.Ticker(ticker)
            df = tkr.history(period=period, interval=interval)

            if df is None or df.empty:
                logger.warning(f"Empty data for {ticker} on attempt {attempt}")
                if attempt < retries:
                    time.sleep(RETRY_DELAY_BASE * attempt)
                continue

            # Standardize columns
            df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
            df.index = pd.to_datetime(df.index)
            df.index = df.index.tz_localize(None)  # Remove timezone for consistency
            df.dropna(inplace=True)

            if len(df) < 50:
                logger.warning(f"Insufficient data for {ticker}: only {len(df)} bars")
                return None

            # Staleness check — last bar should be within 5 trading days
            last_bar = df.index[-1]
            stale_threshold = datetime.now() - timedelta(days=7)
            if last_bar < stale_threshold:
                logger.error(
                    f"STALE DATA for {ticker}: last bar is {last_bar.strftime('%Y-%m-%d')}, "
                    f"threshold is {stale_threshold.strftime('%Y-%m-%d')}. "
                    f"Possible Yahoo throttle or data source failure."
                )
                # Still return but mark as stale via metadata
                df.attrs["stale"] = True
                df.attrs["last_bar"] = last_bar.strftime("%Y-%m-%d")
            else:
                df.attrs["stale"] = False
                df.attrs["last_bar"] = last_bar.strftime("%Y-%m-%d")

            logger.info(f"Fetched {ticker}: {len(df)} bars, last={df.attrs['last_bar']}")
            return df

        except Exception as e:
            logger.error(f"Error fetching {ticker} (attempt {attempt}): {e}")
            if attempt < retries:
                time.sleep(RETRY_DELAY_BASE * attempt)

    logger.error(f"FAILED to fetch {ticker} after {retries} attempts")
    return None


def resample_to_weekly(df: pd.DataFrame) -> pd.DataFrame:
    """Resample daily OHLCV to weekly."""
    weekly = df.resample("W").agg({
        "Open": "first",
        "High": "max",
        "Low": "min",
        "Close": "last",
        "Volume": "sum",
    }).dropna()
    return weekly


def resample_to_monthly(df: pd.DataFrame) -> pd.DataFrame:
    """Resample daily OHLCV to monthly."""
    monthly = df.resample("ME").agg({
        "Open": "first",
        "High": "max",
        "Low": "min",
        "Close": "last",
        "Volume": "sum",
    }).dropna()
    return monthly


def fetch_all_tickers(tickers: list = None) -> dict:
    """
    Fetch daily data for all tickers, returning dict of {ticker: DataFrame}.
    Includes throttle delays between requests.
    """
    if tickers is None:
        tickers = ALL_TICKERS

    results = {}
    for i, ticker in enumerate(tickers):
        df = fetch_ohlcv(ticker)
        if df is not None:
            results[ticker] = df
        else:
            logger.error(f"Skipping {ticker} — no data available")

        # Throttle between requests
        if i < len(tickers) - 1:
            time.sleep(BATCH_DELAY)

    logger.info(f"Fetched {len(results)}/{len(tickers)} tickers successfully")
    return results
