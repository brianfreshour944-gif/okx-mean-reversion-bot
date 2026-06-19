import pandas as pd

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
