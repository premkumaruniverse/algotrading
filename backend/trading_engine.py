import time
import datetime
import pandas as pd
import pandas_ta as ta
from kiteconnect import KiteConnect
from sqlalchemy.orm import Session
from . import crud, models, schemas
from .database import SessionLocal
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TradingEngine")

# Configuration (These could be dynamic or user specific)
INTERVAL = "5minute"
ST_PERIOD = 10
ST_MULTIPLIER = 3
SL_PCT = 0.14
TP_PCT = 0.18
START_TIME = datetime.time(9, 15)
END_TIME = datetime.time(15, 30)

class TradingEngine:
    def __init__(self):
        self.is_running = False
    
    def get_db(self):
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    def get_nifty_expiry(self):
        # Logic to get current month NIFTY Futures symbol
        today = datetime.date.today()
        # simplified: assuming format NIFTY YYMMM FUT e.g. NIFTY 24JAN FUT
        # But symbols are specific. 
        # For now, let's hardcode or fetch from an instrument list if possible.
        # User backtest had: FUT_TOKEN = 12602626
        return "NIFTY FEB FUT" # Placeholder

    def get_instrument_token(self, kite, symbol):
        instruments = kite.instruments("NFO")
        for inst in instruments:
            if inst['tradingsymbol'] == symbol:
                return inst['instrument_token']
        return None

    def get_option_symbol(self, fut_ltp, signal, kite):
        # NIFTY expiry logic needs to be robust.
        # Assuming weekly/monthly expiry.
        # Backtest: NIFTY26JAN...
        # Let's try to find the nearest expiry option.
        
        # Simplified for prototype:
        # We need to know the current expiry string.
        # Let's assume user provides a "base symbol" or we calculate it.
        # This is tricky without live data inspection.
        
        # Heuristic: Get all instruments, filter by NIFTY, find current expiry.
        return None # To be implemented with live data check

    def run_strategy(self):
        logger.info("Trading Engine Heartbeat")
        db = SessionLocal()
        active_users = db.query(models.User).filter(models.User.is_trading_active == True).all()
        
        for user in active_users:
            if not user.access_token or not user.api_key:
                continue
            
            try:
                kite = KiteConnect(api_key=user.api_key)
                kite.set_access_token(user.access_token)
                
                # 1. Get NIFTY FUT Token
                # For this example, I will assume we are trading NIFTY FUT directly or using it for signals
                # We need to look up the token dynamically.
                # Ideally, we cache instruments.
                
                # Dynamic Symbol Lookup (Expensive to do every loop, should cache)
                # For prototype speed, I will search for NIFTY FUT current month
                instruments = kite.instruments("NFO")
                df_inst = pd.DataFrame(instruments)
                
                # Find current month future
                # This is a simplification. Real code needs robust expiry handling.
                current_month_str = datetime.datetime.now().strftime("%y%b").upper() # 24JAN
                fut_symbol_pattern = f"NIFTY {datetime.datetime.now().strftime('%b').upper()} FUT" # NIFTY JAN FUT
                
                # Search for exactly NIFTY JAN FUT (Kite format usually NIFTY24JANFUT or similar)
                # Let's look for name=NIFTY, segment=NFO-FUT
                nifty_futs = df_inst[(df_inst['name'] == 'NIFTY') & (df_inst['segment'] == 'NFO-FUT')]
                nifty_futs = nifty_futs.sort_values('expiry')
                if nifty_futs.empty:
                    logger.error(f"No NIFTY Futures found for user {user.username}")
                    continue
                
                curr_fut = nifty_futs.iloc[0] # Nearest expiry
                fut_token = curr_fut['instrument_token']
                fut_symbol = curr_fut['tradingsymbol'] # e.g., NIFTY24JANFUT
                
                # 2. Get Historical Data
                to_date = datetime.datetime.now()
                from_date = to_date - datetime.timedelta(days=5)
                
                data = kite.historical_data(fut_token, from_date, to_date, INTERVAL)
                df = pd.DataFrame(data)
                if df.empty:
                    continue
                    
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
                
                # 3. Calculate Supertrend
                st = ta.supertrend(df["high"], df["low"], df["close"], length=ST_PERIOD, multiplier=ST_MULTIPLIER)
                if st is None or st.empty:
                    continue
                    
                df = pd.concat([df, st], axis=1)
                
                # Identify Supertrend column (usually SUPERT_7_3.0)
                st_cols = [c for c in df.columns if c.startswith("SUPERT")]
                if not st_cols:
                    continue
                dir_col = [c for c in df.columns if c.startswith("SUPERTd")][0]
                
                last_candle = df.iloc[-1]
                prev_candle = df.iloc[-2]
                
                signal_change = last_candle[dir_col] - prev_candle[dir_col]
                # 2 means Bullish Flip (-1 -> 1), -2 means Bearish Flip (1 -> -1)
                
                fut_ltp = last_candle['close']
                
                # 4. Check Open Positions
                open_trades = crud.get_open_trades(db, user.id)
                
                # EXIT LOGIC
                for trade in open_trades:
                    # Check current price of the option
                    # We need the option token.
                    # In our DB we stored symbol. We need to find token again or store it.
                    # For now let's resolve symbol to token.
                    opt_inst = df_inst[df_inst['tradingsymbol'] == trade.symbol]
                    if opt_inst.empty:
                        continue
                    opt_token = opt_inst.iloc[0]['instrument_token']
                    
                    ltp_data = kite.ltp(opt_token)
                    if str(opt_token) not in ltp_data:
                        continue
                        
                    current_price = ltp_data[str(opt_token)]['last_price']
                    
                    exit_trade = False
                    reason = ""
                    
                    # Target / SL
                    if current_price >= trade.entry_price * (1 + TP_PCT):
                        exit_trade = True
                        reason = "Target Hit"
                    elif current_price <= trade.entry_price * (1 - SL_PCT):
                        exit_trade = True
                        reason = "SL Hit"
                    
                    # Trend Reversal
                    # If Long (CE) and Signal becomes Bearish
                        # if "CE" in trade.symbol and last_candle[dir_col] == -1:
                        #     exit_trade = True
                        #     reason = "Trend Reversal"
                        # # If Short (PE) and Signal becomes Bullish
                        # if "PE" in trade.symbol and last_candle[dir_col] == 1:
                        #     exit_trade = True
                        #     reason = "Trend Reversal"
                        
                    if exit_trade:
                        # Place Sell Order
                        try:
                            order_id = kite.place_order(
                                variety=kite.VARIETY_REGULAR,
                                exchange=kite.EXCHANGE_NFO,
                                tradingsymbol=trade.symbol,
                                transaction_type=kite.TRANSACTION_TYPE_SELL,
                                quantity=trade.quantity,
                                product=kite.PRODUCT_MIS,
                                order_type=kite.ORDER_TYPE_MARKET
                            )
                            logger.info(f"Exited trade {trade.symbol} for user {user.username}: {reason}")
                            crud.close_trade(db, trade.id, current_price, reason)
                        except Exception as e:
                            logger.error(f"Error closing trade: {e}")

                # ENTRY LOGIC
                if not open_trades: # Only one trade at a time per strategy
                    if signal_change == 2: # Bullish -> Buy CE
                        strike = int(round((fut_ltp - 200) / 50) * 50)
                        # Find Expiry
                        # For simplicity, using same expiry as future or nearest weekly
                        # Let's filter options for that strike
                        options = df_inst[
                            (df_inst['name'] == 'NIFTY') & 
                            (df_inst['strike'] == strike) & 
                            (df_inst['instrument_type'] == 'CE')
                        ].sort_values('expiry')
                        
                        if not options.empty:
                            target_opt = options.iloc[0] # Nearest
                            symbol = target_opt['tradingsymbol']
                            
                            # Place Order
                            try:
                                qty = user.num_lots * 65 # NIFTY Lot size
                                order_id = kite.place_order(
                                    variety=kite.VARIETY_REGULAR,
                                    exchange=kite.EXCHANGE_NFO,
                                    tradingsymbol=symbol,
                                    transaction_type=kite.TRANSACTION_TYPE_BUY,
                                    quantity=qty,
                                    product=kite.PRODUCT_MIS,
                                    order_type=kite.ORDER_TYPE_MARKET
                                )
                                # Fetch execution price (simplified: using LTP)
                                ltp_data = kite.ltp(target_opt['instrument_token'])
                                entry_price = ltp_data[str(target_opt['instrument_token'])]['last_price']
                                
                                trade_data = schemas.TradeCreate(
                                    symbol=symbol,
                                    entry_price=entry_price,
                                    quantity=qty,
                                    status="OPEN"
                                )
                                crud.create_trade(db, trade_data, user.id)
                                logger.info(f"Entered CE trade {symbol} for user {user.username}")
                            except Exception as e:
                                logger.error(f"Error entering trade: {e}")

                    elif signal_change == -2: # Bearish -> Buy PE
                        strike = int(round((fut_ltp + 200) / 50) * 50)
                        options = df_inst[
                            (df_inst['name'] == 'NIFTY') & 
                            (df_inst['strike'] == strike) & 
                            (df_inst['instrument_type'] == 'PE')
                        ].sort_values('expiry')
                        
                        if not options.empty:
                            target_opt = options.iloc[0]
                            symbol = target_opt['tradingsymbol']
                            
                            try:
                                qty = user.num_lots * 65 # Lot size 75? Backtest said 65 (maybe old lot size, now it is 25/75 depending on time, assume 75 for Nifty or 25? User code says 65. Let's use user code.)
                                # Wait, user code says LOT_SIZE = 65. I'll stick to user input.
                                
                                order_id = kite.place_order(
                                    variety=kite.VARIETY_REGULAR,
                                    exchange=kite.EXCHANGE_NFO,
                                    tradingsymbol=symbol,
                                    transaction_type=kite.TRANSACTION_TYPE_BUY,
                                    quantity=qty,
                                    product=kite.PRODUCT_MIS,
                                    order_type=kite.ORDER_TYPE_MARKET
                                )
                                ltp_data = kite.ltp(target_opt['instrument_token'])
                                entry_price = ltp_data[str(target_opt['instrument_token'])]['last_price']
                                
                                trade_data = schemas.TradeCreate(
                                    symbol=symbol,
                                    entry_price=entry_price,
                                    quantity=qty,
                                    status="OPEN"
                                )
                                crud.create_trade(db, trade_data, user.id)
                                logger.info(f"Entered PE trade {symbol} for user {user.username}")
                            except Exception as e:
                                logger.error(f"Error entering trade: {e}")

            except Exception as e:
                logger.error(f"Error processing user {user.username}: {e}")
        
        db.close()
