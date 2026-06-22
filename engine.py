"""
FILE: engine.py
FUNCTION: The Analytical Brain.
Contains purely mathematical logic, indicator calculations (ATR, EMA),
and decision-making rules for the bot. No external API calls here.
"""
import pandas as pd   # <-- THIS IS THE MISSING LINE

class TradingEngine:
    @staticmethod
    def calculate_atr(ohlcv, period=14):
        df = pd.DataFrame(ohlcv, columns=['t', 'o', 'h', 'l', 'c', 'v'])
        high_low = df['h'] - df['l']
        high_close = (df['h'] - df['c'].shift()).abs()
        low_close = (df['l'] - df['c'].shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return float(tr.rolling(period).mean().iloc[-1])

    @staticmethod
    def get_ema(closes, period):
        return pd.Series(closes).ewm(span=period, adjust=False).mean().iloc[-1]

    def check_signal(self, ohlcv, multiplier=1.5):
        """
        Mean reversion signal using EMA + ATR (Keltner Channel).
        Returns 'BUY', 'SELL', or 'HOLD'.
        """
        if len(ohlcv) < 20:
            return "HOLD"

        closes = [c[4] for c in ohlcv]
        ema = self.get_ema(closes, period=20)
        atr = self.calculate_atr(ohlcv, period=14)
        current_price = closes[-1]

        upper = ema + atr * multiplier
        lower = ema - atr * multiplier

        if current_price <= lower:
            return "BUY"
        elif current_price >= upper:
            return "SELL"
        else:
            return "HOLD"
