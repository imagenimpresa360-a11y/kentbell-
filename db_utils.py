
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "railway")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "password")
DB_PORT = os.getenv("DB_PORT", "5432")

class DatabaseManager:
    def __init__(self):
        self.conn = None

    def connect(self):
        try:
            self.conn = psycopg2.connect(
                host=DB_HOST,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASS,
                port=DB_PORT
            )
            self.conn.autocommit = False # Handle transactions manually for safety
            return self.conn
        except Exception as e:
            print(f"Error connecting to database: {repr(e)}")
            raise

    def close(self):
        if self.conn:
            self.conn.close()

    def execute_query(self, query, params=None):
        """Execute a query (INSERT/UPDATE/DELETE) and commit."""
        try:
            cur = self.conn.cursor()
            cur.execute(query, params)
            self.conn.commit()
            cur.close()
        except Exception as e:
            self.conn.rollback()
            print(f"Query Error: {e}")
            raise

    def execute_script(self, script_path):
        """Execute a full SQL script file."""
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                sql = f.read()
            cur = self.conn.cursor()
            cur.execute(sql)
            self.conn.commit()
            print(f"Executed script: {script_path}")
            cur.close()
        except Exception as e:
            self.conn.rollback()
            print(f"Script Error: {e}")
            raise

    def fetch_all(self, query, params=None):
        """Fetch all results as a dictionary."""
        try:
            cur = self.conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(query, params)
            rows = cur.fetchall()
            cur.close()
            return rows
        except Exception as e:
            print(f"Fetch Error: {e}")
            raise
