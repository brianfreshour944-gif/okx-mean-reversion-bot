"""
FILE: exchange.py
FUNCTION: The Execution Layer.
Wraps the CCXT library to communicate with the OKX API. 
Handles fetching data, placing orders, and checking balances.
"""
import os
import ccxt
import logging
from utils import log_trade, push_heartbeat

class ExchangeManager:
    def __init__(self):
        self.exchange = ccxt.okx({
            'apiKey': os.getenv('OKX_API_KEY'),
            'secret': os.getenv('OKX_API_SECRET'),
            'password': os.getenv('OKX_PASSPHRASE'),
            'enableRateLimit': True,
            'options': {'defaultType': 'spot', 'x-simulated-trading': '1'}
        })
        self.exchange.set_sandbox_mode(True)
        self.exchange.session.headers.update({'x-simulated-trading': '1'})
        self.exchange.load_markets()

    def fetch_ohlcv(self, symbol, timeframe, limit=50):
        return self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)

    def place_order(self, symbol, side, amount, params=None):
        return self.exchange.create_order(symbol, 'market', side, amount, params=params)

    def get_balance(self, asset):
        balance = self.exchange.fetch_balance()
        return float(balance.get(asset, {}).get('free', 0.0))
