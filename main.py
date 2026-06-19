import time
import logging
from exchange import ExchangeManager
from engine import TradingEngine
from database import DatabaseManager

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run():
    ex = ExchangeManager()
    db = DatabaseManager()
    eng = TradingEngine()
    
    logging.info("🚀 Bot started. Entering main loop...")

    while True:
        try:
            # 1. Heartbeat
            db.execute_query("INSERT INTO bot_status (bot_name, last_update, status) VALUES (%s, NOW(), 'RUNNING') ON CONFLICT (bot_name) DO UPDATE SET last_update = NOW()", ('SOL_BOT',))

            # 2. Logic Example
            ohlcv = ex.fetch_ohlcv('SOL/USDT', '15m')
            closes = [c[4] for c in ohlcv]
            atr = eng.calculate_atr(ohlcv)
            
            logging.info(f"Market update: ATR={atr:.4f}")
            
            # 3. Sleep
            time.sleep(60)
            
        except Exception as e:
            logging.error(f"Main Loop Error: {e}")
            time.sleep(60)

if __name__ == '__main__':
    run()
