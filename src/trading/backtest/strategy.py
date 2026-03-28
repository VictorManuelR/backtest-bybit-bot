from dataclasses import dataclass, asdict
import random
import time
from typing import Any, cast
from datetime import datetime

import pandas as pd
from trading.backtest.ohlcv_data import get_backtest_data

OPENING_FEE = 0.00055  # 0.055%
CLOSING_FEE = 0.0002   # 0.02%

@dataclass
class Operation:
    """Parameters for a single simulated trade (entry, size, and optional exits)."""

    symbol: str
    side: str
    qty: float
    entry_price: float
    stoploss: float | None
    takeprofit: float | None

    def validate(self) -> None:
        """Check side, quantity, and stop/take consistency; warn if exits are missing."""
        if self.side not in ("BUY", "SELL"):
            raise ValueError("ERROR: side must be 'BUY' or 'SELL'")
        if self.qty <= 0:
            raise ValueError("ERROR: 'qty' must be greater than 0.0")
        if self.entry_price is None:
            raise ValueError("ERROR: 'entry_price' can not be None")
        if self.stoploss is not None and self.takeprofit is not None: 
            if self.side == "BUY":
                if self.stoploss > self.takeprofit:
                    raise ValueError("ERROR: 'takeprofit' must be greater than 'stoploss' in a 'BUY' operation.")
            else:
                if self.stoploss < self.takeprofit:
                    raise ValueError("ERROR: 'stoploss' must be greater than 'takeprofit' in a 'SELL' operation.")
        else:
            print("WARNING: No exit points assigned. (tp|sl)")

    def show(self) -> None:
        """Print a human-readable summary of this operation to stdout."""
        print(f"|--> Symbol    : {self.symbol}")
        print(f"|--> Side      : {self.side}")
        print(f"|--> Qty       : {self.qty:.3f}")
        print(f"|--> Price     : {self.entry_price:.3f}")
        print(f"|--> Stoploss  : {self.stoploss if self.stoploss is not None else 'None'}")
        print(f"|--> Takeprofit: {self.takeprofit if self.takeprofit is not None else 'None'}")

    def to_dict(self) -> dict[str, Any]:
        """Return this operation as a plain dict (same keys as the dataclass fields)."""
        return asdict(self)

def strategy(symbol: str, df: pd.DataFrame) -> Operation:
    """Build a random long/short operation from the latest close (example strategy).

    Uses the last row of ``df`` for entry and sets stop/take 1% from entry; size targets ~1000 USDT notional.

    Args:
        symbol: Trading pair symbol (e.g. ``BTCUSDT``).
        df: OHLCV dataframe with at least a ``close`` column.

    Returns:
        A validated :class:`Operation` instance.
    """

    if df.empty:
        raise ValueError("Input dataframe is empty")

    # Define Order Type.
    # In this example it is random.
    side_types = ["BUY", "SELL"]
    side = random.choice(side_types)
    last_close = cast(float, df["close"].iat[-1])
    
    # Assign join point depending on side.
    if side == "BUY":
        entry_price = last_close * 0.99
    else:
        entry_price = last_close * 1.01
        
    # Assign exit points 1.0% away from entry.
    if side == "BUY":
        stoploss = entry_price * 0.99
        takeprofit = entry_price * 1.01
    else:
        stoploss = entry_price * 1.01
        takeprofit = entry_price * 0.99
    
    # Size position to invest 1,000 USDT notionally.
    qty = 1_000 / entry_price
    
    # Validate the operation params
    operation = Operation(symbol=symbol, 
                          side=side, 
                          qty=qty, 
                          entry_price=entry_price, 
                          stoploss=stoploss, 
                          takeprofit=takeprofit)
    operation.validate()
    
    return operation

def simulate_order(df: pd.DataFrame, operation: Operation) -> dict:
    """Walk forward candle-by-candle and simulate fill, exit, and PnL for ``operation``.

    Entry triggers when ``entry_price`` lies between the bar's low and high. Exit is
    stop loss, take profit, or last bar close if still open.

    Args:
        df: OHLCV dataframe with ``datetime_utc``, ``open``, ``high``, ``low``, ``close``.
        operation: Trade to simulate.

    Returns:
        Dict with symbol, side, qty, prices, times, ``pnl``, ``real_pnl`` (after fees),
        ``duration`` (minutes), and ``closed_by`` (reason or ``no_entry_triggered``).
    """
    
    if df.empty:
        raise ValueError("Input dataframe is empty")
    
    trade_open = False
    entry_time: Any = None
    exit_time: Any = None
    exit_price: float | None = None
    closed_by: str | None = None
    
    for row in df.itertuples():     
        row_high = cast(float, row.high)
        row_low = cast(float, row.low)

        if not trade_open:
            if row_high >= operation.entry_price and row_low <= operation.entry_price:
                trade_open = True
                entry_time = row.datetime_utc
        else:
            if operation.side == "BUY":
                if operation.stoploss is not None and row_low <= operation.stoploss:
                    exit_price = float(operation.stoploss)
                    exit_time = row.datetime_utc
                    closed_by = "stoploss"
                    break
                elif operation.takeprofit is not None and row_high >= operation.takeprofit:
                    exit_price = float(operation.takeprofit)
                    exit_time = row.datetime_utc
                    closed_by = "takeprofit"
                    break
                    
            elif operation.side == "SELL":
                if operation.stoploss is not None and row_high >= operation.stoploss:
                    exit_price = float(operation.stoploss)
                    exit_time = row.datetime_utc
                    closed_by = "stoploss"
                    break
                elif operation.takeprofit is not None and row_low <= operation.takeprofit:
                    exit_price = float(operation.takeprofit)
                    exit_time = row.datetime_utc
                    closed_by = "takeprofit"
                    break
    
    if trade_open and exit_price is None:
        last_row = df.iloc[-1]
        exit_price = float(last_row["close"])
        exit_time = last_row["datetime_utc"]
        closed_by = "end_of_data"
    
    if trade_open:
        duration_minutes = None
        if entry_time is not None and exit_time is not None:
            duration = pd.Timestamp(exit_time) - pd.Timestamp(entry_time)
            duration_minutes = int(duration.total_seconds() // 60)
        
        if exit_price is None:
            raise RuntimeError("Trade is open but exit_price is missing")

        if operation.side == "BUY":
            pnl = (exit_price - operation.entry_price) * operation.qty
        else:
            pnl = (operation.entry_price - exit_price) * operation.qty
        
        results = {
            "symbol": operation.symbol,
            "side": operation.side,
            "qty": operation.qty,
            "amount": operation.qty * operation.entry_price,
            "stoploss": operation.stoploss,
            "takeprofit": operation.takeprofit,
            "entry_time": entry_time,
            "exit_time": exit_time,
            "duration": duration_minutes,
            "entry_price": operation.entry_price,
            "exit_price": exit_price,
            "pnl": pnl,
            "real_pnl": pnl - (operation.entry_price * OPENING_FEE + exit_price * CLOSING_FEE) * operation.qty,
            "closed_by": closed_by,
        }
    else:
        results = {
            "symbol": operation.symbol,
            "side": operation.side,
            "qty": operation.qty,
            "amount": operation.qty * operation.entry_price,
            "stoploss": operation.stoploss,
            "takeprofit": operation.takeprofit,
            "entry_time": None,
            "exit_time": None,
            "duration": 0,
            "entry_price": None,
            "exit_price": None,
            "pnl": 0,
            "real_pnl": 0,
            "closed_by": "no_entry_triggered",
        }
    return results

def process_symbol(
    symbol: str,
    date: str,
    format: str,
    timeframe: str,
    backtest_d: int,
    max_living_time_h: int,
    ret_data: bool = False,
) -> dict[str, Any] | tuple[dict[str, Any], pd.DataFrame]:
    """Load OHLCV around ``date``, run :func:`strategy`, then :func:`simulate_order`.

    Intended to run per symbol (e.g. in a worker). Retries ``get_backtest_data`` up to
    three times on failure with a short sleep.

    Args:
        symbol: Trading pair symbol.
        date: Anchor date string parsed with ``format``.
        format: ``strftime`` format for ``date``.
        timeframe: Higher timeframe for history before the anchor (e.g. ``2h``).
        backtest_d: Days of history before the anchor.
        max_living_time_h: Hours of 1m bars after the anchor for the simulation window.
        ret_data: If True, return ``(results, df_after)``; else only ``results``.

    Returns:
        Simulation result dict, or a tuple ``(results, df_after)`` when ``ret_data`` is True.

    Raises:
        Exception: Re-raises errors from strategy/simulation after successful data load.
    """

    last_error: Exception | None = None
    df_before: pd.DataFrame | None = None
    df_after: pd.DataFrame | None = None

    for attempt in range(1, 4):
        try:
            df_before, df_after = get_backtest_data(
                "linear",
                symbol,
                timeframe,
                date=(date, format),
                days_before=backtest_d,
                hours_after=max_living_time_h,
            )
            break
        except Exception as e:
            last_error = e
            print(f"Error: {e}. ({attempt}) Retrying...")
            time.sleep(2)
    else:
        raise RuntimeError("Failed to load backtest data after 3 attempts") from last_error

    if df_before is None or df_after is None:
        raise RuntimeError("Backtest dataframes were not initialized")

    operation = strategy(symbol=symbol, df=df_before)
    results = simulate_order(df=df_after, operation=operation)
    if ret_data:
        return results, df_after
    return results
