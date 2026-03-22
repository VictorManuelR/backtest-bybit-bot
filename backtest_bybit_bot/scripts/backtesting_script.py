from trading.utils.dates import dates_generator
from trading.backtest.strategy import process_symbol
from trading.utils.files import save_to_csv
import pandas as pd
import time

start = "2028-02-01"
end   = "2028-02-28"
fmt   = "%Y-%m-%d"

vBOT = "0.0.1"

dir_path = "backtesting"
filename = f"results_{vBOT}.csv"

INITIAL_CAPITAL = 100_000  
capital = INITIAL_CAPITAL 
amount_per_trade = 1_000

dates = dates_generator(start, end, fmt)
ticks = ["BTCUSDT", "XRPUSDT", "ETHUSDT"]

if __name__ == "__main__":
    start_time = time.time()
    for date in dates:

        results = [process_symbol(symbol, date, fmt, "15m", 1, 8) for symbol in ticks]
        df = pd.DataFrame(results)
        
        if df.empty:
            print(f"No operations launched at {date}\n")
            continue
        else:
            print(f"{len(df)} operations launched at {date}\n")
            
        df["version"] = vBOT
        df["started_at"] = date
        df['capital'] = 0.0
        df['leverage'] = 1
        df['result'] = df['real_pnl'].apply(lambda x: 'WON' if x > 0 else ('LOST' if x < 0 else None))
        
        # --- Actualización de capital diaria ---
        daily_pnl = df["real_pnl"].sum()
        
        for idx, row in df.iterrows():
            capital += row['real_pnl']
            df.loc[idx, "capital"] = capital
        print(f"Capital actualizado tras {date}: {capital:.2f}")
        
        save_to_csv(df, dir_path, filename)
        
        print("Completed!\n")

    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"Elapsed time: {elapsed_time:.2f} seconds")