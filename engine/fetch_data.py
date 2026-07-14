"""
fetch_data.py — OHLCV data fetcher with bulk-download, retries, and staleness detection.
Downloads all IHSG (~900+) and US (S&P 500) stock symbols dynamically from GitHub sources,
falling back to solid curated lists if network requests fail.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict

import pandas as pd
import yfinance as yf
import requests

logger = logging.getLogger(__name__)

# Fallback lists in case dynamic load fails
FALLBACK_IHSG = [
    "BBCA.JK", "BBRI.JK", "TLKM.JK", "BMRI.JK", "ASII.JK", "BBNI.JK", "UNVR.JK", 
    "ICBP.JK", "PGAS.JK", "ADRO.JK", "KLBF.JK", "GOTO.JK", "AMRT.JK", "BRPT.JK",
    "TPIA.JK", "UNTR.JK", "INDF.JK", "CPIN.JK", "SMGR.JK", "INKP.JK", "PTBA.JK",
    "HRUM.JK", "ITMG.JK", "MEDC.JK", "ANTM.JK", "INCO.JK", "BUKA.JK", "BRIS.JK"
]

FALLBACK_US = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "BRK-B", "JNJ", 
    "V", "TSM", "PG", "AVGO", "XOM", "MA", "UNH", "HD", "JPM", "LLY", "ABBV"
]

# We will populate these dynamically at runtime
ALL_TICKERS = []
MARKET_MAP = {}

def get_ihsg_tickers() -> List[str]:
    """Fetch all active Indonesian Stock Exchange tickers from wildangunawan/Dataset-Saham-IDX."""
    try:
        url = "https://raw.githubusercontent.com/wildangunawan/Dataset-Saham-IDX/main/List%20Emiten/all.csv"
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            lines = res.text.split("\n")
            tickers = []
            for line in lines[1:]: # skip header
                parts = line.strip().split(",")
                if parts and len(parts[0]) == 4: # Standard 4 letter tickers
                    tickers.append(f"{parts[0]}.JK")
            if tickers:
                logger.info(f"Loaded {len(tickers)} IHSG tickers from GitHub dataset.")
                return tickers
    except Exception as e:
        logger.warning(f"Failed to fetch dynamic IHSG list ({e}). Using fallback list.")
    return FALLBACK_IHSG

def get_us_tickers() -> List[str]:
    """Fetch S&P 500 constituents from datasets/s-and-p-500-companies."""
    try:
        url = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv"
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            lines = res.text.split("\n")
            tickers = []
            for line in lines[1:]: # skip header
                parts = line.strip().split(",")
                if parts and len(parts[0]) > 0:
                    tickers.append(parts[0].replace(".", "-")) # yfinance format for BRK.B is BRK-B
            if tickers:
                logger.info(f"Loaded {len(tickers)} US tickers from S&P 500 dataset.")
                return tickers
    except Exception as e:
        logger.warning(f"Failed to fetch dynamic US list ({e}). Using fallback list.")
    return FALLBACK_US

# Initialize universes
try:
    logger.info("Initializing ticker universes...")
    ihsg = get_ihsg_tickers()
    us = get_us_tickers()
    ALL_TICKERS = ihsg + us
    for t in ihsg:
        MARKET_MAP[t] = "IHSG"
    for t in us:
        MARKET_MAP[t] = "US"
except Exception as e:
    logger.error(f"Error initializing ticker list: {e}")
    ALL_TICKERS = FALLBACK_IHSG + FALLBACK_US
    for t in FALLBACK_IHSG:
        MARKET_MAP[t] = "IHSG"
    for t in FALLBACK_US:
        MARKET_MAP[t] = "US"


def resample_to_weekly(df: pd.DataFrame) -> pd.DataFrame:
    """Resample daily OHLCV to weekly."""
    if df is None or df.empty:
        return None
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
    if df is None or df.empty:
        return None
    monthly = df.resample("ME").agg({
        "Open": "first",
        "High": "max",
        "Low": "min",
        "Close": "last",
        "Volume": "sum",
    }).dropna()
    return monthly


def fetch_all_tickers(tickers: List[str] = None, batch_size: int = 80) -> Dict[str, pd.DataFrame]:
    """
    Fetch daily data for all tickers in parallel batches.
    Returns a dictionary of {ticker: DataFrame}.
    """
    if tickers is None:
        tickers = ALL_TICKERS

    results = {}
    logger.info(f"Starting batch fetch for {len(tickers)} tickers (batch size: {batch_size})")

    # Divide tickers into batches
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i + batch_size]
        logger.info(f"Processing batch {i // batch_size + 1}/{(len(tickers) - 1) // batch_size + 1} ({len(batch)} tickers)")
        
        try:
            # Fetch batch in parallel
            data = yf.download(
                tickers=batch,
                period="2y",
                interval="1d",
                group_by="ticker",
                threads=True,
                progress=False,
                timeout=20
            )
            
            # Extract individual stock dataframes
            for ticker in batch:
                try:
                    if isinstance(data.columns, pd.MultiIndex):
                        if ticker not in data.columns.levels[0]:
                            continue
                        df = data[ticker].copy()
                    else:
                        df = data.copy()
                    
                    df.dropna(subset=["Close"], inplace=True)
                    if df.empty or len(df) < 30:
                        continue
                    
                    # Clean up columns and index
                    df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
                    df.index = pd.to_datetime(df.index)
                    df.index = df.index.tz_localize(None)
                    
                    # Check for staleness
                    last_bar = df.index[-1]
                    stale_threshold = datetime.now() - timedelta(days=7)
                    stale = last_bar < stale_threshold
                    
                    df.attrs["stale"] = stale
                    df.attrs["last_bar"] = last_bar.strftime("%Y-%m-%d")
                    
                    results[ticker] = df
                except Exception as ex:
                    logger.debug(f"Error parsing ticker {ticker} in batch: {ex}")
                    
        except Exception as e:
            logger.error(f"Error downloading batch: {e}")
            
        # Small sleep between batches to avoid IP blocks
        time.sleep(2)

    logger.info(f"Successfully fetched {len(results)}/{len(tickers)} tickers.")
    return results
