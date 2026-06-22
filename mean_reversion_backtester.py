"""
FILE: mean_reversion_backtester.py
FUNCTION: Backtests the mean reversion strategy using the REAL engine.py.
"""
import pandas as pd
import numpy as np
import yfinance as yf
from engine import TradingEngine  # Your actual engine

class MeanReversionBacktester:
    def __init__(self, symbol, multiplier=1.5, capital=1000, trade_size=0.1):
        self.symbol = symbol
        self.multiplier = float(multiplier)
        self.capital = float(capital)
        self.trade_size = float(trade_size)
        self.data = None

    def fetch_data(self, start_date, end_date):
        print(f"📥 Fetching {self.symbol} from {start_date} to {end_date}...")
        self.data = yf.download(self.symbol, start=start_date, end=end_date)
        if self.data.empty:
            print("❌ No data returned.")
        else:
            print(f"✅ Downloaded {len(self.data)} bars.")
        return self.data

    def run(self):
        if self.data is None or self.data.empty:
            return {}

        df = self.data.copy()
        engine = TradingEngine()  # Uses the check_signal we added

        # Convert to list of rows: [Open, High, Low, Close, Volume]
        data_rows = df.values.tolist()
        closes = [row[3] for row in data_rows]

        cash = self.capital
        holdings = 0.0
        trades = []

        for idx, row in enumerate(data_rows):
            # Build OHLCV list in the format engine expects: [t, o, h, l, c, v]
            # Use index as timestamp (or a dummy timestamp)
            ohlcv = [
                [idx, row[0], row[1], row[2], row[3], row[4]]
            ]
            signal = engine.check_signal(ohlcv, multiplier=self.multiplier)
            price = row[3]  # Close price

            if signal == "BUY" and holdings == 0:
                cost = price * self.trade_size
                if cost <= cash:
                    cash -= cost
                    holdings = self.trade_size
                    trades.append({'type': 'BUY', 'price': price})
                    print(f"BUY at {price:.2f}")
            elif signal == "SELL" and holdings > 0:
                cash += price * holdings
                trades.append({'type': 'SELL', 'price': price})
                holdings = 0
                print(f"SELL at {price:.2f}")

        # Close remaining position at last price
        if holdings > 0:
            last_price = closes[-1]
            cash += last_price * holdings
            trades.append({'type': 'SELL (close)', 'price': last_price})
            holdings = 0

        net_profit = cash - self.capital
        total_trades = len([t for t in trades if t['type'] == 'SELL'])

        # Win Rate
        buys = [t for t in trades if t['type'] == 'BUY']
        sells = [t for t in trades if t['type'] in ('SELL', 'SELL (close)')]
        profits = []
        for buy, sell in zip(buys, sells):
            pnl = (sell['price'] - buy['price']) * self.trade_size
            profits.append(pnl)

        win_rate = (sum(1 for p in profits if p > 0) / len(profits) * 100) if profits else 0.0

        # Sharpe (safe)
        daily_returns = df['Close'].pct_change().dropna()
        sharpe = 0.0
        if not daily_returns.empty:
            std = daily_returns.std()
            if hasattr(std, 'iloc'):
                std = std.iloc[0]
            if std != 0:
                sharpe = (daily_returns.mean() / std) * np.sqrt(252)
        if hasattr(sharpe, 'iloc'):
            sharpe = sharpe.iloc[0]
        sharpe = float(sharpe)

        # Max Drawdown (safe)
        cumulative = df['Close'].pct_change().cumsum().fillna(0)
        running_max = cumulative.expanding().max()
        denom = running_max.abs().replace(0, 1)
        drawdown = (cumulative - running_max) / denom
        max_drawdown_pct = drawdown.min() * 100 if not drawdown.empty else 0.0
        if hasattr(max_drawdown_pct, 'iloc'):
            max_drawdown_pct = max_drawdown_pct.iloc[0]
        max_drawdown_pct = float(max_drawdown_pct)

        print(f"\n📊 Mean Reversion Backtest Results for {self.symbol}:")
        print(f"   Multiplier: {self.multiplier}")
        print(f"   Total Trades: {total_trades}")
        print(f"   Net Profit: ${net_profit:.2f}")
        print(f"   Win Rate: {win_rate:.2f}%")
        print(f"   Sharpe: {sharpe:.2f}")
        print(f"   Max Drawdown: {max_drawdown_pct:.2f}%")

        return {
            'total_trades': total_trades,
            'net_profit': net_profit,
            'win_rate': win_rate,
            'sharpe': sharpe,
            'max_drawdown_pct': max_drawdown_pct,
        }
