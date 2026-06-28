"""
FILE: exchange.py
FUNCTION: The Execution Layer.

FIX: place_order() previously called log_trade() from utils.py, which only
pushed to an unconfigured "Base44" API and never reached Postgres -- so
every fill on OKX was invisible to the dashboard. It now takes a db
(DatabaseManager) instance and writes directly to the trades table, the
same pattern already working in okx-grid-bot. update_status() had the same
problem with push_heartbeat() and is fixed the same way.
"""
import os
import ccxt
import logging

class ExchangeManager:
    def __init__(self, bot_name="okx-mean-reversion-bot"):
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

    def get_quote_balance(self, quote_currency="USDT"):
        """Returns available balance of the quote currency (e.g. USDT),
        so the caller can size/skip orders instead of firing blind and
        hitting an insufficient-balance error on every loop."""
        try:
            balance = self.exchange.fetch_balance()
            return float(balance.get(quote_currency, {}).get('free', 0) or 0)
        except Exception as e:
            logging.error(f"❌ Failed to fetch balance: {e}")
            return 0.0

    def get_total_equity(self):
        """Returns this account's total equity in USD (cash + all held
        positions, marked to market), using OKX's own totalEq figure
        rather than summing per-currency balances ourselves.

        NOTE: this account is in OKX sandbox/demo mode (see __init__) --
        the number returned here is demo money, not real funds. The
        dashboard's equity tracking labels this appropriately as long as
        OKX_SANDBOX reporting stays consistent with how the dashboard
        reads it."""
        try:
            balance = self.exchange.fetch_balance()
            data = balance.get('info', {}).get('data', [])
            if data and 'totalEq' in data[0] and data[0]['totalEq']:
                return float(data[0]['totalEq'])
            # Fallback: sum eqUsd across all currency details
            total = 0.0
            for d in data:
                for detail in d.get('details', []):
                    total += float(detail.get('eqUsd', 0) or 0)
            return total
        except Exception as e:
            logging.error(f"❌ Failed to fetch total equity: {e}")
            return 0.0

    # Required for order execution
    def place_order(self, db, symbol, side, amount, price=0.0, params=None):
        """
        Executes a market order and logs the confirmed fill to Postgres.
        Returns the order dict on success, None on failure -- caller must
        check for None and not assume the order filled.
        """
        try:
            order = self.exchange.create_order(symbol, 'market', side, amount, params=params)

            execution_price = order.get('price') or order.get('average') or price
            execution_qty = order.get('filled') or amount
            order_id = order.get('id', 'unknown')
            fee = 0.0
            if order.get('fee') and order['fee'].get('cost'):
                fee = float(order['fee']['cost'])

            db.log_trade(
                bot_name=self.bot_name,
                exchange="okx",
                symbol=symbol,
                side=side,
                price=float(execution_price),
                qty=float(execution_qty),
                order_id=order_id,
                fee=fee,
            )
            return order
        except Exception as e:
            logging.error(f"❌ Order deployment failed: {e}")
            db.log_error(self.bot_name, f"Order failed: {side} {symbol} qty={amount}: {e}")
            return None

    # Required for dashboard heartbeat
    def update_status(self, db, status="RUNNING"):
        db.update_status(self.bot_name, status)
