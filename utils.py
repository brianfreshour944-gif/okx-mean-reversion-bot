# utils.py

def log_trade(bot_name, symbol, side, qty, entry_price, pnl=None, **kwargs):
    # Validation logic
    if entry_price is None or float(entry_price) <= 0:
        return
    
    # You can access extra items via kwargs if needed
    order_id = kwargs.get('order_id')
    
    payload = {
        "bot_name": bot_name,
        "symbol": symbol,
        "side": side,
        "qty": float(qty),
        "entry_price": float(entry_price),
        "pnl": pnl,
        "order_id": order_id
    }
    # ... your requests.post logic ...
