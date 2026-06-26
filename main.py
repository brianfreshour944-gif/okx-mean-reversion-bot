"""
FILE: main.py
FUNCTION: The Orchestrator.
Coordinates the Engine, Exchange, and Database modules to
execute the trading strategy in a continuous loop.

FIX: This loop previously only fetched OHLCV and logged ATR -- it never
called engine.check_signal() or exchange.place_order(), so the bot could
run forever without ever trading. It now evaluates the mean-reversion
signal every iteration, tracks an open/closed position across restarts
(via bot_status.in_position/entry_price), and checks USDT balance before
buying so it doesn't loop forever hitting an insufficient-balance error
like alpaca-trend-following-bot did.
"""
import os
import time
import logging
from exchange import ExchangeManager
from engine import TradingEngine
from database import DatabaseManager

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BOT_NAME = os.getenv("BOT_NAME", "okx-mean-reversion-bot")
SYMBOL = os.getenv("TRADING_SYMBOL", "SOL/USDT")
TIMEFRAME = os.getenv("TRADING_TIMEFRAME", "15m")

# Position sizing: spend this many USDT per BUY (env-overridable, mirrors
# GRID_CAPITAL_USDT in okx-grid-bot). Keeping this modest avoids the
# Alpaca bot's "requested more than available balance" retry loop.
TRADE_USDT = float(os.getenv("TRADE_USDT", "50"))
POLL_SECONDS = int(os.getenv("POLL_SECONDS", "60"))
ATR_MULTIPLIER = float(os.getenv("ATR_MULTIPLIER", "1.5"))


def run():
    ex = ExchangeManager(bot_name=BOT_NAME)
    db = DatabaseManager()
    eng = TradingEngine()

    db.ensure_schema()

    logging.info(f"🚀 Bot started. symbol={SYMBOL} timeframe={TIMEFRAME} "
                 f"trade_usdt={TRADE_USDT} poll={POLL_SECONDS}s")

    in_position, entry_price = db.load_position_state(BOT_NAME)
    logging.info(f"Loaded position state -> in_position={in_position} entry_price={entry_price}")

    while True:
        try:
            if db.check_status(BOT_NAME) == 'STOP':
                logging.info("🛑 Stop signal detected in database. Exiting loop.")
                break

            ohlcv = ex.fetch_ohlcv(SYMBOL, TIMEFRAME)
            current_price = ohlcv[-1][4]
            signal = eng.check_signal(ohlcv, multiplier=ATR_MULTIPLIER)
            logging.info(f"📈 [TICK] {SYMBOL} price={current_price} signal={signal} "
                         f"in_position={in_position}")

            if signal == "BUY" and not in_position:
                usdt_balance = ex.get_quote_balance("USDT")
                if usdt_balance < TRADE_USDT:
                    logging.warning(f"🚫 Skipping BUY -- balance ${usdt_balance:.2f} "
                                     f"is below trade size ${TRADE_USDT:.2f}")
                else:
                    qty = TRADE_USDT / current_price
                    logging.info(f"🎯 BUY signal triggered for {SYMBOL}. Placing order...")
                    order = ex.place_order(db, SYMBOL, "buy", qty, current_price)
                    if order is not None:
                        in_position = True
                        entry_price = current_price
                        db.save_position_state(BOT_NAME, in_position, entry_price)
                        logging.info(f"✅ Position opened. Entry tracked at: {entry_price}")

            elif signal == "SELL" and in_position:
                # Spot trading: sell the same quantity we originally bought.
                # Re-derive qty from entry_price/TRADE_USDT rather than
                # assuming current balance is exactly our position size.
                qty = TRADE_USDT / entry_price if entry_price else 0
                if qty <= 0:
                    logging.warning("🚫 Skipping SELL -- no valid entry_price on record.")
                else:
                    logging.info(f"🛑 SELL signal triggered for {SYMBOL}. Placing order...")
                    order = ex.place_order(db, SYMBOL, "sell", qty, current_price)
                    if order is not None:
                        in_position = False
                        entry_price = 0.0
                        db.save_position_state(BOT_NAME, in_position, entry_price)
                        logging.info("✅ Position closed.")

            ex.update_status(db, "RUNNING")

        except Exception as e:
            logging.error(f"Main Loop Error: {e}")
            try:
                db.log_error(BOT_NAME, str(e))
            except Exception:
                pass

        time.sleep(POLL_SECONDS)


if __name__ == '__main__':
    run()
