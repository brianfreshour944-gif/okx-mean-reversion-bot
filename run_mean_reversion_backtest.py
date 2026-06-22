"""
FILE: run_mean_reversion_backtest.py
FUNCTION: Runs mean reversion backtest and saves to DB.
"""
from mean_reversion_backtester import MeanReversionBacktester
from datetime import date
from database import DatabaseManager  # Uses your existing DatabaseManager class

def save_backtest_result(bot_name, strategy_name, start_date, end_date, results):
    db = DatabaseManager()
    query = """
        INSERT INTO backtest_results 
        (bot_name, strategy_name, start_date, end_date, total_trades, net_profit, sharpe_ratio, max_drawdown_pct, win_rate)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    params = (
        bot_name,
        strategy_name,
        start_date,
        end_date,
        results['total_trades'],
        results['net_profit'],
        round(results['sharpe'], 2),
        round(results['max_drawdown_pct'], 2),
        round(results['win_rate'], 2)
    )
    try:
        db.execute_query(query, params)
        print(f"✅ Inserted backtest for {bot_name}")
    except Exception as e:
        print(f"❌ Failed to insert for {bot_name}: {e}")

def run_mean_reversion_backtest():
    # Define your mean reversion bot – adjust multiplier, trade_size, capital
    bots = [
        {
            "bot_name": "okx-mean-reversion-bot",  # Must match exactly
            "symbol": "SOL-USD",                   # Your bot uses SOL/USDT on OKX
            "multiplier": 1.5,                     # Keltner channel width
            "capital": 1000,
            "trade_size": 0.1,                     # SOL per trade
        },
    ]

    start_date = "2025-01-01"
    end_date = date.today().strftime("%Y-%m-%d")

    for cfg in bots:
        print(f"\n🚀 Running mean reversion backtest for {cfg['bot_name']} on {cfg['symbol']}...")
        backtester = MeanReversionBacktester(
            symbol=cfg['symbol'],
            multiplier=cfg['multiplier'],
            capital=cfg['capital'],
            trade_size=cfg['trade_size']
        )
        backtester.fetch_data(start_date, end_date)
        results = backtester.run()
        if results:
            save_backtest_result(
                bot_name=cfg['bot_name'],
                strategy_name=f"Keltner_{cfg['multiplier']}x",
                start_date=start_date,
                end_date=end_date,
                results=results
            )
        else:
            print(f"⚠️ No results for {cfg['bot_name']}")

if __name__ == "__main__":
    run_mean_reversion_backtest()
