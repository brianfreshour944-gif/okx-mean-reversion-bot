"""
FILE: database.py
FUNCTION: The Memory/Persistence Layer.
Manages the PostgreSQL connection pool. Handles heartbeat status
updates and logs trade history to the database.

FIX: log_trade() previously didn't exist here at all -- exchange.py imported
a stub log_trade from utils.py that only POSTed to an unconfigured "Base44"
API and never touched Postgres. This file is now the single source of truth
for all DB writes (trades, status, errors, position state), matching the
pattern used by the other bots in this fleet.
"""
import os
import logging
import psycopg2
from psycopg2 import pool

# load_dotenv()  <-- DELETED

class DatabaseManager:
    def __init__(self):
        # Now it ONLY uses the system environment variable (same as your other bots)
        self.db_url = os.getenv('DATABASE_URL')
        try:
            self.pool = psycopg2.pool.SimpleConnectionPool(1, 5, self.db_url)
            logging.info("✅ Database connection pool initialized.")
        except Exception as e:
            logging.error(f"❌ Failed to create DB pool: {e}")
            raise

    def execute_query(self, query, params=None):
        """Helper to run INSERT/UPDATE/DELETE queries safely."""
        conn = self.pool.getconn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(query, params)
        except Exception as e:
            logging.error(f"DB Query Error: {e}")
        finally:
            self.pool.putconn(conn)

    def fetch_one(self, query, params=None):
        """Helper to fetch a single result (e.g., for stop signals)."""
        conn = self.pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(query, params)
                return cur.fetchone()
        except Exception as e:
            logging.error(f"DB Fetch Error: {e}")
            return None
        finally:
            self.pool.putconn(conn)

    def ensure_schema(self):
        """
        Defensive schema setup. Creates bot_status/trades/bot_errors if they
        don't exist, and adds any columns this bot specifically needs
        (in_position, entry_price) if an older version of the table is
        already in place from another bot. Safe to call on every startup --
        this is exactly the kind of silent column mismatch that caused
        log_trade_to_db to fail invisibly for another bot in this fleet.
        """
        conn = self.pool.getconn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS bot_status (
                            bot_name TEXT PRIMARY KEY,
                            status TEXT DEFAULT 'STOP',
                            last_update TIMESTAMP DEFAULT NOW(),
                            session_start_time TIMESTAMP,
                            in_position BOOLEAN DEFAULT FALSE,
                            entry_price NUMERIC DEFAULT 0
                        )
                    """)
                    cur.execute("ALTER TABLE bot_status ADD COLUMN IF NOT EXISTS in_position BOOLEAN DEFAULT FALSE")
                    cur.execute("ALTER TABLE bot_status ADD COLUMN IF NOT EXISTS entry_price NUMERIC DEFAULT 0")
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS trades (
                            id SERIAL PRIMARY KEY,
                            bot_name TEXT,
                            exchange TEXT,
                            symbol TEXT,
                            side TEXT,
                            price NUMERIC,
                            quantity NUMERIC,
                            value NUMERIC,
                            fee NUMERIC DEFAULT 0,
                            order_id TEXT,
                            realized_pnl NUMERIC DEFAULT 0,
                            timestamp TIMESTAMP DEFAULT NOW()
                        )
                    """)
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS bot_errors (
                            id SERIAL PRIMARY KEY,
                            bot_name TEXT,
                            error_message TEXT,
                            timestamp TIMESTAMP DEFAULT NOW()
                        )
                    """)
            logging.info("✅ [DEBUG] ensure_schema completed (created/verified bot_status, trades, bot_errors).")
        except Exception as e:
            logging.error(f"❌ [CRITICAL] ensure_schema FAILED: {e}")
        finally:
            self.pool.putconn(conn)

    def log_trade(self, bot_name, symbol, side, price, qty, order_id, exchange="okx", fee=0.0, realized_pnl=0.0):
        """
        Single source of truth for trade logging. Mirrors the validated,
        working pattern from okx-grid-bot's database.py. Rejects rows with
        non-positive price/qty instead of silently writing garbage.
        """
        if price is None or qty is None or float(price) <= 0 or float(qty) <= 0:
            logging.warning(f"⚠️ Rejected trade log with invalid price/qty: price={price} qty={qty}")
            return
        value = float(price) * float(qty)
        self.execute_query("""
            INSERT INTO trades (bot_name, exchange, symbol, side, price, quantity, value, fee, order_id, realized_pnl, timestamp)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """, (bot_name, exchange, symbol, side, float(price), float(qty), value, float(fee), str(order_id), float(realized_pnl)))
        logging.info(f"✅ [DEBUG] log_trade succeeded for {bot_name} -> {side} {qty} {symbol} @ {price}")

    def log_error(self, bot_name, error_msg):
        self.execute_query(
            "INSERT INTO bot_errors (bot_name, error_message, timestamp) VALUES (%s, %s, NOW())",
            (bot_name, str(error_msg))
        )

    def update_status(self, bot_name, status):
        """
        Updates the live runtime heartbeat in bot_status. Creates the row
        if it doesn't exist yet (same UPSERT-by-hand pattern as the other
        bots so behavior is consistent across the fleet).
        """
        conn = self.pool.getconn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE bot_status SET status = %s, last_update = NOW()
                        WHERE bot_name = %s
                    """, (status, bot_name))
                    if cur.rowcount == 0:
                        cur.execute("""
                            INSERT INTO bot_status (bot_name, status, last_update, session_start_time)
                            VALUES (%s, %s, NOW(), NOW())
                        """, (bot_name, status))
        except Exception as e:
            logging.error(f"❌ [CRITICAL] update_status FAILED: {e}")
        finally:
            self.pool.putconn(conn)

    def check_status(self, bot_name):
        """Returns the bot's current status string, defaulting to RUNNING
        if no row exists yet (mirrors okx-grid-bot's check_status)."""
        row = self.fetch_one("SELECT status FROM bot_status WHERE bot_name = %s", (bot_name,))
        return row[0] if row else 'RUNNING'

    def save_position_state(self, bot_name, in_position, entry_price):
        """Persists whether we're currently holding a position, so a
        restart doesn't forget and buy into an already-open position."""
        self.execute_query("""
            INSERT INTO bot_status (bot_name, in_position, entry_price, last_update)
            VALUES (%s, %s, %s, NOW())
            ON CONFLICT (bot_name) DO UPDATE
            SET in_position = EXCLUDED.in_position, entry_price = EXCLUDED.entry_price, last_update = NOW()
        """, (bot_name, in_position, float(entry_price)))

    def load_position_state(self, bot_name):
        """Returns (in_position: bool, entry_price: float)."""
        row = self.fetch_one(
            "SELECT in_position, entry_price FROM bot_status WHERE bot_name = %s", (bot_name,)
        )
        if not row:
            return False, 0.0
        return bool(row[0]), float(row[1] or 0.0)
