"""
FILE: exchange.py
FUNCTION: The Execution Layer.
"""
import os
import ccxt
import logging
from utils import log_trade, push_heartbeat

class ExchangeManager:
    def __init__(self, bot_name="Grok_OKX_Apex"):
        self.bot_name = bot_name
        self.exchange = ccxt.okx({
            'apiKey': os.getenv('OKX_API_KEY'),
            'secret': os.getenv('OKX_API_SECRET'),
            'password': os.getenv('OKX_PASSPHRASE'),
            'enableRateLimit': True,
            'options': {'defaultType': 'spot', 'x-simulated-trading': '1'}
        })
        self.exchange.set_sandbox_mode(True)
        self.exchange.load_markets()

    def place_order(self, symbol, side, amount, price=None, params=None):
        # 1. Execute the trade
        order = self.exchange.create_order(symbol, 'market', side, amount, params=params)
        
        # 2. Log to dashboard automatically
        log_trade(
            bot_name=self.bot_name,
            symbol=symbol,
            side=side, # 'buy' or 'sell'
            qty=float(amount),
            entry_price=float(price or 0.0), # Ensure your bot passes the current price
            order_id=order.get('id')
        )
        return order

    def update_status(self, equity, buying_power, daily_pnl):
        # Call this periodically from your main loop
        push_heartbeat(
            bot_name=self.bot_name,
            equity=equity,
            buying_power=buying_power,
            daily_pnl=daily_pnl
        )
