"""
FILE: run_grid_backtests.py
FUNCTION: Runs grid backtests for OKX bots and saves results to DB.
"""
from grid_backtester import GridBacktester
from datetime import date
import database as db  # Your bot's database.py

def save_backtest_result(bot_name, strategy_name, start_date, end_date, results):
    try:
        with db.get_db_connection() as conn, conn.cursor() as cur:
            cur.execute("""
                INSERT INTO backtest_results 
                (bot_name, strategy_name, start_date, end_date, total_trades, net_profit, sharpe_ratio, max_drawdown_pct, win_rate)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                bot_name,
                strategy_name,
                start_date,
                end_date,
                results['total_trades'],
                results['net_profit'],
                round(results['sharpe'], 2),
                round(results['max_drawdown_pct'], 2),
                round(results['win_rate'], 2)
            ))
            conn.commit()
        print(f"✅ Inserted backtest for {bot_name}")
    except Exception as e:
        print(f"❌ Failed to insert for {bot_name}: {e}")

def run_all_grid_backtests():
    bots = [
        {
            "bot_name": "okx_grid_bot",      # Must match exactly what's in bot_status
            "symbol": "DOGE-USD",
            "levels": 5,
            "step": 3.0,
            "capital": 1000,
            "trade_size": 100,
        },
        {
            "bot_name": "Static-Repo-okx-bot",
            "symbol": "DOGE-USD",
            "levels": 7,
            "step": 2.5,
            "capital": 1000,
            "trade_size": 100,
        },
    ]

    start_date = "2025-01-01"
    end_date = date.today().strftime("%Y-%m-%d")

    for cfg in bots:
        print(f"\n🚀 Running grid backtest for {cfg['bot_name']} on {cfg['symbol']}...")
        backtester = GridBacktester(
            symbol=cfg['symbol'],
            levels=cfg['levels'],
            step_percent=cfg['step'],
            capital=cfg['capital'],
            trade_size=cfg['trade_size']
        )
        backtester.fetch_data(start_date, end_date)
        results = backtester.run()
        if results:
            save_backtest_result(
                bot_name=cfg['bot_name'],
                strategy_name=f"Grid_{cfg['levels']}levels_{cfg['step']}step",
                start_date=start_date,
                end_date=end_date,
                results=results
            )
        else:
            print(f"⚠️ No results for {cfg['bot_name']}")

if __name__ == "__main__":
    run_all_grid_backtests()
