import numpy as np
import mplfinance as mpf

def find_candle(df, value):
    """Return index labels of rows where ``value`` lies between ``low`` and ``high`` (inclusive).

    Args:
        df: DataFrame with at least ``low`` and ``high`` columns.
        value: Price level to test against each candle's range.

    Returns:
        List of matching index labels, or ``[None]`` if no row contains ``value``.
    """
    # Creamos una máscara booleana donde cada elemento indica
    # si la vela incluye 'value' en el rango [low, high].
    mask = (df["low"] <= value) & (df["high"] >= value)
    
    # Obtenemos los índices de las filas que cumplen la condición
    indices = df.index[mask].tolist()
    
    if len(indices) > 0:
        return indices
    else:
        return [None]

def plot_trades_scatter(df_trades, df_dict, volume: bool = False):
    """Plot each completed trade as candlestick chart with entry/exit markers and SL/TP lines.

    Skips rows where ``closed_by == "no_entry_triggered"`` or ``entry_price`` is missing.
    Expects ``df_dict[symbol]`` to be OHLCV with ``datetime_utc`` and ``duration`` in bar count.

    Args:
        df_trades: DataFrame of trades (must expose attributes used in ``itertuples()``).
        df_dict: Map symbol -> OHLCV dataframe for plotting.
        volume: Whether to show volume subplot (passed to ``mplfinance.plot``).
    """
    for trade in df_trades.itertuples():
        
        symbol = trade.symbol
        side = trade.side
        entry_price = trade.entry_price
        exit_price  = trade.exit_price
        sl = trade.stoploss
        tp = trade.takeprofit

        if trade.closed_by == "no_entry_triggered": continue
        if entry_price is None: continue
        
        df_after = df_dict[symbol]
        
        rows = len(df_after)
        entry = np.full(rows, np.nan)
        exit = np.full(rows, np.nan)

        entry_idx = find_candle(df_after, trade.entry_price)[0]
        
        if entry_idx is None:
            entry_idx = 0
        
        exit_idx = trade.duration

        exit[entry_idx + exit_idx] = exit_price
        entry[entry_idx] = entry_price
        
        if side == "BUY":
            sp1 = mpf.make_addplot(exit, type='scatter', markersize=50, color=('red' if exit_price < entry_price else 'green'))
        else:
            sp1 = mpf.make_addplot(exit, type='scatter', markersize=50, color=('red' if exit_price > entry_price else 'green'))
   
        sp2 = mpf.make_addplot(entry, type='scatter', markersize=50, color='blue')
    
        # display(trade)
    
        chart=df_after.set_index('datetime_utc')
        mpf.plot(
            chart,
            type='candle',
            style='yahoo',
            title=f"{symbol} | side: {trade.side}, result: {trade.result}",
            addplot=[sp1, sp2],
            hlines=dict(hlines=[tp,sl, entry_price],colors=['g','r','black'],linestyle='-.', alpha=0.5),
            volume=volume,
            ylabel="Price"
        )
