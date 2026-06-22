"""
FILE: grid_backtester.py
FUNCTION: Backtests a grid strategy on historical OHLC data.
"""
import pandas as pd
import numpy as np
import yfinance as yf

class GridBacktester:
    def __init__(self, symbol, levels=5, step_percent=3.0, capital=1000, trade_size=100):
        self.symbol = symbol
        self.levels = int(levels)
        self.step_percent = float(step_percent) / 100.0
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

        # --- Convert to list of rows for safe iteration ---
        # Each row: [Open, High, Low, Close, Volume] (in that order)
        data_rows = df.values.tolist()
        closes = [row[3] for row in data_rows]  # Close is index 3

        # Center price = average of first 10 closes
        center = float(np.mean(closes[:10]))

        buy_levels = [center * (1 - self.step_percent * i) for i in range(1, self.levels + 1)]
        sell_levels = [center * (1 + self.step_percent * i) for i in range(1, self.levels + 1)]

        print(f"🎯 Center: {center:.4f} | Levels: {self.levels} | Step: {self.step_percent*100:.1f}%")

        cash = self.capital
        holdings = 0.0
        trades = []

        # Iterate over rows (each row is a list: [Open, High, Low, Close, Volume])
        for row in data_rows:
            high = row[1]   # High
            low = row[2]    # Low

            # BUY
            for level in buy_levels:
                if low <= level and cash >= level * self.trade_size:
                    cash -= level * self.trade_size
                    holdings += self.trade_size
                    trades.append({'type': 'BUY', 'price': level, 'qty': self.trade_size})
                    print(f"BUY at {level:.2f}")
                    break

            # SELL
            if holdings > 0:
                for level in sell_levels:
                    if high >= level:
                        sell_qty = min(holdings, self.trade_size)
                        cash += level * sell_qty
                        holdings -= sell_qty
                        trades.append({'type': 'SELL', 'price': level, 'qty': sell_qty})
                        print(f"SELL at {level:.2f}")
                        break

        # Close remaining position at last price
        if holdings > 0:
            last_price = closes[-1]   # already a float
            cash += last_price * holdings
            trades.append({'type': 'SELL (close)', 'price': last_price, 'qty': holdings})
            holdings = 0

        net_profit = cash - self.capital
        total_trades = len([t for t in trades if t['type'] == 'SELL'])

        # Win Rate
        buys = [t for t in trades if t['type'] == 'BUY']
        sells = [t for t in trades if t['type'] in ('SELL', 'SELL (close)')]
        profits = []
        for buy, sell in zip(buys, sells):
            pnl = (sell['price'] - buy['price']) * buy['qty']
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

        print(f"\n📊 Grid Backtest Results for {self.symbol}:")
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
