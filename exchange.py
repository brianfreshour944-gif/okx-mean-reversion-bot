"""
FILE: exchange.py
FUNCTION: The Execution Layer.
"""
import os
import ccxt
import logging
from utils import log_trade, push_heartbeat
from exchange_okx import ExchangeManager

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

    # Required by main.py
    def fetch_ohlcv(self, symbol, timeframe, limit=50):
        return self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)

    # Required for order execution
    def place_order(self, symbol, side, amount, price=0.0, params=None):
        order = self.exchange.create_order(symbol, 'market', side, amount, params=params)
        log_trade(
            bot_name=self.bot_name,
            symbol=symbol,
            side=side,
            qty=float(amount),
            entry_price=float(price),
            order_id=order.get('id')
        )
        return order

    # Required for dashboard heartbeat
    def update_status(self, equity, buying_power, daily_pnl):
        push_heartbeat(
            bot_name=self.bot_name,
            equity=equity,
            buying_power=buying_power,
            daily_pnl=daily_pnl
        )
