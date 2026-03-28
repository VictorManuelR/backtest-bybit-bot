from datetime import timedelta

import pandas as pd
from trading.exchange.bybit import get_ohlcv_data
from trading.utils.dates import datetime_from_string, timestamp_from_datetime

def get_backtest_data(
    category: str,
    symbol: str,
    timeframe: str,
    date: tuple[str, str],
    days_before: int = 10,
    hours_after: int = 1,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fetch OHLCV before and after an anchor instant for backtesting.

    Loads ``timeframe`` history ending at (but excluding) the anchor bar, and 1m bars
    for ``hours_after`` hours starting at the anchor.

    Args:
        category: Bybit category (e.g. ``linear``).
        symbol: Trading pair symbol.
        timeframe: Candle interval for the pre-anchor series (e.g. ``2h``).
        date: ``[date_string, strftime_format]`` for the anchor instant (e.g. ``["2023-01-01 00:00:00", "%Y-%m-%d %H:%M:%S"]``).
        days_before: Days of history before the anchor (for the higher timeframe series).
        hours_after: Hours of 1m data after the anchor.

    Returns:
        Tuple ``(ohlcv_before, ohlcv_after)`` as DataFrames.

    Raises:
        ValueError: If computed end is before start (should not occur with positive ``days_before``).
    """
    if days_before < 0:
        raise ValueError("days_before must be >= 0")
    if hours_after <= 0:
        raise ValueError("hours_after must be > 0")

    end_date = datetime_from_string(date[0], date[1])
    start_date = end_date - timedelta(days=days_before)
    start_ts = timestamp_from_datetime(start_date, units="ms")
    end_ts = timestamp_from_datetime(end_date, units="ms")
    
    if end_date < start_date:
        raise ValueError(f"end date can not be lower than start date")
    
    ohlcv_before = get_ohlcv_data(category, symbol, timeframe,
                                start = start_ts,
                                end   = end_ts,
                                limit = 1000)

    if ohlcv_before.empty:
        raise ValueError("No pre-anchor candles were returned for the selected window")

    # Drop the anchor candle to avoid look-ahead in backtests.
    ohlcv_before = ohlcv_before.iloc[:-1].copy()
    
    ohlcv_after = get_ohlcv_data(category, symbol, "1m",
                                start = end_ts,
                                limit = 60*hours_after)
    return ohlcv_before, ohlcv_after
