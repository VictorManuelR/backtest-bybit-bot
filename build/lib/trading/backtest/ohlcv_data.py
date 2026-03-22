from trading.exchange.bybit import get_ohlcv_data
from trading.utils.dates import datetime_from_string, timestamp_from_datetime
from datetime import timedelta

def get_backtest_data(
    category: str,
    symbol: str,
    timeframe: str,
    date: list,
    days_before: int = 10,
    hours_after: int = 1,
):
    """Fetch OHLCV before and after an anchor instant for backtesting.

    Loads ``timeframe`` history ending at (but excluding) the anchor bar, and 1m bars
    for ``hours_after`` hours starting at the anchor.

    Args:
        category: Bybit category (e.g. ``linear``).
        symbol: Trading pair symbol.
        timeframe: Candle interval for the pre-anchor series (e.g. ``2h``).
        date: ``[date_string, strftime_format]`` for the anchor instant.
        days_before: Days of history before the anchor (for the higher timeframe series).
        hours_after: Hours of 1m data after the anchor.

    Returns:
        Tuple ``(ohlcv_before, ohlcv_after)`` as DataFrames.

    Raises:
        ValueError: If computed end is before start (should not occur with positive ``days_before``).
    """
    end_date = datetime_from_string(date[0], date[1])
    start_date = end_date - timedelta(days=days_before)
    start_ts = timestamp_from_datetime(start_date, units="ms")
    
    if end_date < start_date:
        raise ValueError(f"end date can not be lower than start date")
    
    ohlcv_before = get_ohlcv_data(category, symbol, timeframe,
                                start = start_ts,
                                end   = timestamp_from_datetime(end_date, units="ms"),
                                limit = 1000)
    
    ohlcv_before.drop(ohlcv_before.index[-1], inplace=True)
    
    ohlcv_after = get_ohlcv_data(category, symbol, "1m",
                                start = timestamp_from_datetime(end_date, units="ms"),
                                limit = 60*hours_after)
    return ohlcv_before, ohlcv_after
