import pandas as pd
import pandas_ta as ta
import datetime
from kiteconnect import KiteConnect

# ============================================================
# CONFIGURATION
# ============================================================
API_KEY = "esc4dbeqzbq7h477"
ACCESS_TOKEN = "2O7o7rwWPWwiZb4oOrn4RP3qKtrUHQqP"

FUT_TOKEN = 15150594  # NIFTY FEB FUT
INTERVAL = "5minute"
LOT_SIZE = 65        
NUM_LOTS = 1 
TOTAL_QTY = LOT_SIZE * NUM_LOTS

ST_PERIOD = 10
ST_MULTIPLIER = 3
SL_PCT = 0.12
TP_PCT = 0.18

START_TIME = datetime.time(9, 20)
END_TIME = datetime.time(15, 15)
EXPIRY_PREFIX = "NIFTY26JAN" # Update based on current month/year

# ============================================================
# KITE INITIALIZATION
# ============================================================
kite = KiteConnect(api_key=API_KEY)
kite.set_access_token(ACCESS_TOKEN)

# Fetch NFO instruments once and create a dictionary for O(1) lookup speed
all_instruments = kite.instruments("NFO")
instrument_lookup = {inst['tradingsymbol']: inst['instrument_token'] for inst in all_instruments}

def get_option_token(symbol):
    return instrument_lookup.get(symbol)

# ============================================================
# BACKTEST ENGINE
# ============================================================
def run_backtest(df_fut):
    # Calculate Supertrend
    st = ta.supertrend(df_fut["high"], df_fut["low"], df_fut["close"], length=ST_PERIOD, multiplier=ST_MULTIPLIER)
    df_fut = pd.concat([df_fut, st], axis=1)
    dir_col = [c for c in df_fut.columns if c.startswith("SUPERTd")][0]
    df_fut["signal_change"] = df_fut[dir_col].diff()

    trades = []
    current_pos = None
    opt_token = None
    entry_premium = 0
    entry_info = {}

    print(f"\n{'TIMESTAMP':<20} | {'SIGNAL':<15} | {'FUT PRICE':<10} | {'ACTION'}")
    print("-" * 75)

    for index, row in df_fut.iterrows():
        fut_ltp = row["close"]
        signal = row["signal_change"]
        curr_time = index.time()

        # Log the Signal Change even if not trading
        if signal == 2:
            print(f"{str(index):<20} | BULLISH FLIP  | {fut_ltp:<10.2f} | Checking Entry...")
        elif signal == -2:
            print(f"{str(index):<20} | BEARISH FLIP  | {fut_ltp:<10.2f} | Checking Entry...")

        # --- ENTRY LOGIC ---
        if current_pos is None:
            if START_TIME <= curr_time <= END_TIME:
                if signal == 2 or signal == -2:
                    # Strike Selection (ITM)
                    if signal == 2:
                        strike = int(round((fut_ltp - 200) / 50) * 50)
                        symbol = f"{EXPIRY_PREFIX}{strike}CE"
                        current_pos = "CE"
                    else:
                        strike = int(round((fut_ltp + 200) / 50) * 50)
                        symbol = f"{EXPIRY_PREFIX}{strike}PE"
                        current_pos = "PE"

                    opt_token = get_option_token(symbol)
                    if opt_token:
                        try:
                            # Get Real Premium at the signal candle
                            opt_hist = kite.historical_data(opt_token, index.date(), index.date(), INTERVAL)
                            opt_df = pd.DataFrame(opt_hist).set_index("date")
                            
                            if index in opt_df.index:
                                entry_premium = opt_df.loc[index, "close"]
                                entry_info = {"time": index, "symbol": symbol, "token": opt_token}
                                print(f"{' '*20} | ENTRY TRIGGER | {symbol:<10} | Price: {entry_premium}")
                            else:
                                current_pos = None
                        except Exception:
                            current_pos = None
                    else:
                        print(f"Error: Symbol {symbol} not found in NFO list.")
                        current_pos = None

        # --- EXIT LOGIC ---
        elif current_pos is not None:
            try:
                opt_hist_now = kite.historical_data(opt_token, index.date(), index.date(), INTERVAL)
                opt_df_now = pd.DataFrame(opt_hist_now).set_index("date")
                
                if index in opt_df_now.index:
                    current_premium = opt_df_now.loc[index, "close"]
                else:
                    continue

                exit_trade = False
                reason = ""

                # Conditions
                if current_premium >= entry_premium * (1 + TP_PCT):
                    exit_trade, reason = True, "Target Hit"
                elif current_premium <= entry_premium * (1 - SL_PCT):
                    exit_trade, reason = True, "SL Hit"
                elif (current_pos == "CE" and signal == -2) or (current_pos == "PE" and signal == 2):
                    exit_trade, reason = True, "Trend Rev"
                elif curr_time >= END_TIME:
                    exit_trade, reason = True, "EOD Exit"

                if exit_trade:
                    pnl = (current_premium - entry_premium) * TOTAL_QTY
                    trades.append({
                        "Entry Time": entry_info["time"],
                        "Exit Time": index,
                        "Option": entry_info["symbol"],
                        "Signal": f"{fut_ltp:<10.2f}",
                        "Buy": entry_premium,
                        "Sell": current_premium,
                        "P/L": round(pnl, 2),
                        "Reason": reason
                    })
                    print(f"{str(index):<20} | EXIT TRIGGER  | {entry_info['symbol']:<10} | PnL: {pnl:.2f} ({reason})")
                    current_pos = None
            except:
                continue

    return pd.DataFrame(trades)

# ============================================================
# EXECUTION
# ============================================================
try:
    to_date = datetime.datetime.now()
    from_date = to_date - datetime.timedelta(days=23) # Test with 1 week
    
    data = kite.historical_data(FUT_TOKEN, from_date, to_date, INTERVAL)
    df_fut = pd.DataFrame(data).set_index("date")

    results = run_backtest(df_fut)

    if not results.empty:
        print("\n" + "="*100)
        print(f"FINAL REPORT | LOTS: {NUM_LOTS} | TOTAL QTY: {TOTAL_QTY}")
        print("="*100)
        print(results.to_string(index=False))
        print("="*100)
        print(f"TOTAL NET PROFIT/LOSS: ₹{results['P/L'].sum():,.2f}")
    else:
        print("\nNo trades executed in the given period.")

except Exception as e:
    print(f"Main Error: {e}")