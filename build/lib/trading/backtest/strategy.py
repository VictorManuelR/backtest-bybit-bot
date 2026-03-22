import pandas as pd
from dataclasses import dataclass, asdict
from trading.backtest.ohlcv_data import get_backtest_data
import random
import time

opening_fee = 0.00055  # 0.055%
closing_fee = 0.0002   # 0.02%

@dataclass
class Operation:
    """Parameters for a single simulated trade (entry, size, and optional exits)."""

    symbol: str
    side: str
    qty: float
    entry_price: float
    stoploss: float | None
    takeprofit: float | None

    def validate(self):
        """Check side, quantity, and stop/take consistency; warn if exits are missing."""
        if self.side not in ("BUY", "SELL"):
            raise ValueError("ERROR: side must be 'BUY' or 'SELL'")
        if self.qty <= 0:
            raise ValueError("ERROR: 'qty' must be greater than 0.0")
        if self.entry_price is None:
            raise ValueError("ERROR: 'qty' must be greater than 0.0")
        if self.stoploss is not None and self.takeprofit is not None: 
            if self.side == "BUY":
                if self.stoploss > self.takeprofit:
                    raise ValueError("ERROR: 'takeprofit' must be greater than 'stoploss' in a 'BUY' operation.")
            else:
                if self.stoploss < self.takeprofit:
                    raise ValueError("ERROR: 'stoploss' must be greater than 'takeprofit' in a 'SELL' operation.")
        else:
            print("WARNING: No exit points asigned. (tf|sl)")

    def show(self):
        """Print a human-readable summary of this operation to stdout."""
        print(f"|--> Symbol    : {self.symbol}")
        print(f"|--> Side      : {self.side}")
        print(f"|--> Qty       : {self.qty:.3f}")
        print(f"|--> Price     : {self.entry_price:.3f}")
        print(f"|--> Stoploss  : {self.stoploss:.3f}")
        print(f"|--> Takeprofit: {self.takeprofit:.3f}")

    def to_dict(self):
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

    # Define Order Type
    # In this example I'll do it randomly.
    side_types = ["BUY", "SELL"]
    side = random.choice(side_types)
    
    # Asign Join Point
    # In this example I'll do it depending on the side
    if side == "BUY":
        # if BUY, then the join point will be below the current price by 1.0%
        entry_price = df['close'].iat[-1] * 0.99
    else:
        # if SELL, then the join point will be above the current price by 1.0%
        entry_price = df['close'].iat[-1] * 1.01
        
    # Asign exit points: stoploss and takeprofit
    # In this example I'll do it by asigning each one 1.0% away from the entry price
    if side == "BUY":
        # if BUY, then the stoploss should be below de entry price
        stoploss   = entry_price * 0.99
        takeprofit = entry_price * 1.01
    else:
        # if SELL, then the stoploss should be above de entry price
        stoploss   = entry_price * 1.01
        takeprofit = entry_price * 0.99
    
    # Asing QTY for the operation
    # In this example I'll use the entry price to invest 1,000 USDT
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
    
    details = operation.to_dict()
    
    trade_open = False
    entry_time = None
    exit_time = None
    exit_price = None
    closed_by = None
    
    for row in df.itertuples():     
        if not trade_open:
            if row.high >= details["entry_price"] and row.low <= details["entry_price"]:
                trade_open = True
                entry_time = row.datetime_utc
        else:
            if details["side"] == "BUY":
                if row.low <= details["stoploss"]:
                    exit_price = details["stoploss"]
                    exit_time = row.datetime_utc
                    closed_by = "stoploss"
                    break
                elif row.high >= details["takeprofit"]:
                    exit_price = details["takeprofit"]
                    exit_time = row.datetime_utc
                    closed_by = "takeprofit"
                    break
                    
            elif details["side"] == "SELL":
                if row.high >= details["stoploss"]:
                    exit_price = details["stoploss"]
                    exit_time = row.datetime_utc
                    closed_by = "stoploss"
                    break
                elif row.low <= details["takeprofit"]:
                    exit_price = details["takeprofit"]
                    exit_time = row.datetime_utc
                    closed_by = "takeprofit"
                    break
    
    if trade_open and exit_price is None:
        last_row = df.iloc[-1]
        exit_price = last_row["close"]
        exit_time = last_row["datetime_utc"]
        closed_by = "end_of_data"
    
    if trade_open:
        duration_minutes = None
        if entry_time is not None and exit_time is not None:
            duration = pd.to_datetime(exit_time) - pd.to_datetime(entry_time)
            duration_minutes = int(duration.total_seconds() // 60)
        
        if details["side"] == "BUY":
            pnl = (exit_price - details["entry_price"]) * details["qty"]
        else:
            pnl = (details["entry_price"] - exit_price) * details["qty"]
        
        results = {
            'symbol'     : details["symbol"],
            'side'       : details["side"],
            'qty'        : details["qty"],
            'amount'     : details["qty"] * details["entry_price"],
            'stoploss'   : details["stoploss"],
            'takeprofit' : details["takeprofit"],
            'entry_time' : entry_time,
            'exit_time'  : exit_time,
            'duration'   : duration_minutes,
            'entry_price': details["entry_price"],
            'exit_price' : exit_price,
            'pnl'        : pnl,
            'real_pnl'   : pnl - (details["entry_price"] * opening_fee + exit_price * closing_fee) * details["qty"],
            'closed_by'  : closed_by,
        }
    else:
        results = {
            'symbol'     : details["symbol"],
            'side'       : details["side"],
            'qty'        : details["qty"],
            'amount'     : details["qty"] * details["entry_price"],
            'stoploss'   : details["stoploss"],
            'takeprofit' : details["takeprofit"],
            'entry_time' : None,
            'exit_time'  : None,
            'duration'   : 0,
            'entry_price': None,
            'exit_price' : None,
            'pnl'        : 0,
            'real_pnl'   : 0,
            'closed_by'  : "no_entry_triggered"
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
) -> dict:
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

    count = 0
    while count < 3:
        try:
            df_before, df_after = get_backtest_data("linear", symbol, timeframe,
                                                    date = [date, format],
                                                    days_before = backtest_d, hours_after = max_living_time_h)
            break
        except Exception as e:
            count+=1
            print(f"Error: {e}. ({count})Retrying...")
            time.sleep(2)

    try:
        operation = strategy(symbol=symbol, df=df_before)
        results = simulate_order(df=df_after, operation=operation)
        if ret_data:
            return results, df_after
        else:
            return results
    except Exception:
        raise
