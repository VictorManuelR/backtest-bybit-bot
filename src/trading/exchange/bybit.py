from typing import Any

import pandas as pd
import requests
from trading.utils.dates import timestamp_from_datetime, datetime_from_string

BYBIT_TESTNET_KLINE_URL = "https://api-testnet.bybit.com/v5/market/kline"

TIMEFRAME_INTERVAL = {
    "1m"  : "1",
    "3m"  : "3",
    "5m"  : "5",
    "15m" : "15",
    "30m" : "30",
    "1h"  : "60",   
    "2h"  : "120",
    "4h"  : "240",
    "6h"  : "360",
    "12h" : "720",
    "1d"  : "D",
    "1w"  : "W",
    "1M"  : "M"
    }

class BybitAPIError(Exception):
    """Raised when Bybit responds with an API-level error."""

def get_klines(params: dict) -> Any:
    """GET Bybit v5 kline (candles) from testnet; ``params`` are passed as query string."""
    try:
        response = requests.get(BYBIT_TESTNET_KLINE_URL, params=params, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise ConnectionError(f"Request to Bybit failed: {exc}") from exc

def parse_ohlcvt(data: list) -> pd.DataFrame:
    """Turn raw Bybit kline rows into a sorted DataFrame with typed columns and ``datetime_utc``."""
    columns = ["start_time_ms", "open", "high", "low", "close", "volume", "turnover"]

    df = pd.DataFrame(data, columns=columns)

    df = df.astype({
        "start_time_ms": "int64",
        "open"         : "float64",
        "high"         : "float64",
        "low"          : "float64",
        "close"        : "float64",
        "volume"       : "float64",
        "turnover"     : "float64"
    })
    
    df["datetime_utc"] = pd.to_datetime(df["start_time_ms"], unit="ms")

    df.sort_values("start_time_ms").reset_index(drop=True, inplace=True)
    
    return df

def get_ohlcv_data(
    category: str,
    symbol: str,
    timeframe: str,
    start: int | float | None = None,
    end: int | float | None = None,
    limit: int | None = None,
    drop: str | None = None,
) -> pd.DataFrame:
    """Fetch OHLCV (+ turnover) from Bybit testnet and return a parsed DataFrame.

    Args:
        category: Market category (e.g. ``linear``).
        symbol: Trading pair.
        timeframe: Key from ``timeframe_interval`` (e.g. ``5m``, ``1h``).
        start: Start time in milliseconds (API ``start``).
        end: End time in milliseconds (API ``end``).
        limit: Max candles returned.
        drop: Column to drop from the dataframe (e.g. ``turnover``).

    Returns:
        Parsed dataframe with OHLCV data.
    """
    interval = TIMEFRAME_INTERVAL.get(timeframe)
    if interval is None:
        available = ", ".join(TIMEFRAME_INTERVAL.keys())
        raise ValueError(f"Invalid timeframe '{timeframe}'. Valid values: {available}")

    params: dict[str, Any] = {
        "category": category,
        "symbol": symbol,
        "interval": interval,
    }
    if start is not None:
        params["start"] = int(start)
    if end is not None:
        params["end"] = int(end)
    if limit is not None:
        params["limit"] = int(limit)
    
    response = get_klines(params)
    if response["retCode"] != 0:
        raise BybitAPIError(f"API error {response['retCode']}: {response['retMsg']}")

    data = response["result"]["list"]
    ohlcvt_data = parse_ohlcvt(data)
    if drop is not None:
        if drop not in ohlcvt_data.columns:
            available = ", ".join(ohlcvt_data.columns)
            raise ValueError(f"Column '{drop}' not found. Available columns: {available}")
        ohlcvt_data.drop(drop, axis=1, inplace=True)
    return ohlcvt_data
