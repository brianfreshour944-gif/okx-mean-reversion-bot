import os
import logging
import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv

load_dotenv()

class DatabaseManager:
    def __init__(self):
        # Coolify injects this environment variable automatically
        self.db_url = os.getenv('DATABASE_URL')
        try:
            # We initialize a pool of 1 to 5 connections
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
            self.pool.putconn(conn)
        except Exception as e:
            logging.error(f"DB Query Error: {e}")
            self.pool.putconn(conn)

    def fetch_one(self, query, params=None):
        """Helper to fetch a single result (e.g., for stop signals)."""
        conn = self.pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(query, params)
                result = cur.fetchone()
            self.pool.putconn(conn)
            return result
        except Exception as e:
            logging.error(f"DB Fetch Error: {e}")
            self.pool.putconn(conn)
            return None
