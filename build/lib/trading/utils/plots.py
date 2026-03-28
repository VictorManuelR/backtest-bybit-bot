import numpy as np
import pandas as pd
import mplfinance as mpf
from typing import Any, cast

def find_candle(df: pd.DataFrame, value: float) -> list[int]:
    """Return row positions where ``value`` lies between ``low`` and ``high`` (inclusive).

    Args:
        df: DataFrame with at least ``low`` and ``high`` columns.
        value: Price level to test against each candle's range.

    Returns:
        List of matching row positions.
    """

    mask = (df["low"] <= value) & (df["high"] >= value)

    idxs = np.where(mask.to_numpy())[0].tolist()
    return idxs

def _safe_float(value: Any) -> float | None:
    """Convert values to float when possible, otherwise return None."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

def plot_trades_scatter(
    df_trades: pd.DataFrame,
    df_dict: dict[str, pd.DataFrame],
    volume: bool = False,
) -> None:
    """Plot each completed trade as candlestick chart with entry/exit markers and SL/TP lines.

    Skips rows where ``closed_by == "no_entry_triggered"`` or ``entry_price`` is missing.
    Expects ``df_dict[symbol]`` to be OHLCV with ``datetime_utc`` and ``duration`` in bar count.

    Args:
        df_trades: DataFrame of trades (must expose attributes used in ``itertuples()``).
        df_dict: Map symbol -> OHLCV dataframe for plotting.
        volume: Whether to show volume subplot (passed to ``mplfinance.plot``).
    """
    required_trade_cols = {"symbol", "side", "entry_price", "exit_price", "stoploss", "takeprofit", "duration", "closed_by"}
    missing_trade_cols = required_trade_cols.difference(df_trades.columns)
    if missing_trade_cols:
        missing = ", ".join(sorted(missing_trade_cols))
        raise ValueError(f"df_trades is missing required columns: {missing}")

    for trade in df_trades.itertuples():
        symbol = cast(str, trade.symbol)
        side = cast(str, trade.side)
        entry_price = _safe_float(trade.entry_price)
        exit_price = _safe_float(trade.exit_price)
        sl = _safe_float(trade.stoploss)
        tp = _safe_float(trade.takeprofit)

        if trade.closed_by == "no_entry_triggered":
            continue
        if entry_price is None or exit_price is None:
            continue
        if symbol not in df_dict:
            continue

        df_after = df_dict[symbol]
        if df_after.empty:
            continue
        required_ohlcv_cols = {"datetime_utc", "high", "low", "close"}
        missing_ohlcv_cols = required_ohlcv_cols.difference(df_after.columns)
        if missing_ohlcv_cols:
            missing = ", ".join(sorted(missing_ohlcv_cols))
            raise ValueError(f"OHLCV dataframe for '{symbol}' is missing columns: {missing}")

        rows = len(df_after)
        entry = np.full(rows, np.nan)
        exit = np.full(rows, np.nan)

        entry_matches = find_candle(df_after, entry_price)
        if not entry_matches:
            continue
        entry_idx = entry_matches[0]

        duration = _safe_float(trade.duration)
        exit_idx = int(duration) if duration is not None else 0
        plot_exit_idx = min(max(entry_idx + exit_idx, 0), rows - 1)

        exit[plot_exit_idx] = exit_price
        entry[entry_idx] = entry_price
        
        if side == "BUY":
            sp1 = mpf.make_addplot(exit, type="scatter", markersize=50, color=("red" if exit_price < entry_price else "green"))
        else:
            sp1 = mpf.make_addplot(exit, type="scatter", markersize=50, color=("red" if exit_price > entry_price else "green"))
   
        sp2 = mpf.make_addplot(entry, type="scatter", markersize=50, color="blue")

        chart = df_after.set_index("datetime_utc")

        hline_values = [entry_price]
        hline_colors = ["black"]
        if tp is not None:
            hline_values.append(tp)
            hline_colors.append("g")
        if sl is not None:
            hline_values.append(sl)
            hline_colors.append("r")

        real_pnl = _safe_float(getattr(trade, "real_pnl", None))
        pnl_text = f"{real_pnl:.2f}" if real_pnl is not None else "n/a"

        mpf.plot(
            chart,
            type="candle",
            style="yahoo",
            title=f"{symbol} | side: {side} | real_pnl: {pnl_text} | closed_by: {trade.closed_by}",
            addplot=[sp1, sp2],
            hlines=dict(hlines=hline_values, colors=hline_colors, linestyle="-.", alpha=0.5),
            volume=volume,
            ylabel="Price"
        )
