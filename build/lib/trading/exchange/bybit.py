import requests
import pandas as pd

timeframe_interval = {
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

def get_klines(params: dict):
    """GET Bybit v5 kline (candles) from testnet; ``params`` are passed as query string."""
    url = "https://api-testnet.bybit.com/v5/market/kline"
    response = requests.get(url, params=params)
    return  response.json()

def parse_ohlcvt(data: list) -> pd.DataFrame:
    """Turn raw Bybit kline rows into a sorted DataFrame with typed columns and ``datetime_utc``."""
    columns = ["start_time_ms", "open", "high", "low", "close", "volume", "turnover"]

    df = pd.DataFrame(data, columns=columns)

    df = df.astype({
        "start_time_ms": "int64",
        "open": "float64",
        "high": "float64",
        "low": "float64",
        "close": "float64",
        "volume": "float64",
        "turnover": "float64"
    })
    
    df["datetime_utc"] = pd.to_datetime(df["start_time_ms"], unit="ms")

    df = df.sort_values("start_time_ms")
    df = df.reset_index(drop=True)

    return df

def get_ohlcv_data(
    category: str,
    symbol: str,
    timeframe: str,
    start: int | None = None,
    end: int | None = None,
    limit: int | None = None,
    turnover: bool = True,
) -> pd.DataFrame:
    """Fetch OHLCV (+ turnover) from Bybit testnet and return a parsed DataFrame.

    Args:
        category: Market category (e.g. ``linear``).
        symbol: Trading pair.
        timeframe: Key from ``timeframe_interval`` (e.g. ``5m``, ``1h``).
        start: Start time in milliseconds (API ``start``).
        end: End time in milliseconds (API ``end``).
        limit: Max candles returned.
        turnover: If False, attempts to drop turnover column (see implementation).

    Returns:
        Parsed dataframe, or ``1`` on API/parse error (legacy behavior).
    """
    params = {
        "category" : category,
        "symbol"   : symbol,
        "interval" : timeframe_interval[timeframe],
        "start"    : start,
        "end"      : end,
        "limit"    : limit
    }
    
    try:
        response = get_klines(params)
        if response['retCode'] != 0:
            print(f'Error {response['retCode']}: {response['retMsg']}')
            return 1
        else:
            data = response['result']['list']
            ohlcvt_data = parse_ohlcvt(data)
            if turnover is False:
                ohlcvt_data.drop("turnover", axis=1)
            return ohlcvt_data
    except Exception as e:
        print(f'Error: {e}')
        return 1
