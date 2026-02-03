import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

# Load/Create .env file
env_path = '.env'
if not os.path.exists(env_path):
    print("Creating .env file with default credentials...")
    with open(env_path, 'w') as f:
        f.write("DB_NAME=crossfit_control\n")
        f.write("DB_USER=postgres\n")
        f.write("DB_PASS=password\n")
        f.write("DB_HOST=localhost\n")
        f.write("DB_PORT=5432\n")

load_dotenv()

DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')

def create_database():
    try:
        # Connect to default 'postgres' db to create the new db
        conn = psycopg2.connect(
            user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT, dbname='postgres'
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        
        # Check if exists
        cur.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{DB_NAME}'")
        exists = cur.fetchone()
        
        if not exists:
            print(f"Creating database '{DB_NAME}'...")
            cur.execute(f"CREATE DATABASE \"{DB_NAME}\"")
        else:
            print(f"Database '{DB_NAME}' already exists.")
            
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error creating database: {e}")
        print("Please check your credentials in .env file.")
        return False

def init_schema():
    try:
        conn = psycopg2.connect(
            user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT, dbname=DB_NAME
        )
        cur = conn.cursor()
        
        print("Executing schema.sql...")
        with open('schema.sql', 'r', encoding='utf-8') as f:
            schema_sql = f.read()
            cur.execute(schema_sql)
            
        conn.commit()
        print("Schema applied successfully!")
        
        # Verify categories
        cur.execute("SELECT name FROM expense_categories")
        cats = cur.fetchall()
        print("\nRegistered Categories:")
        for c in cats:
            print(f"- {c[0]}")
            
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error applying schema: {e}")
        return False

if __name__ == "__main__":
    print(f"--- DATABASE INITIALIZER ({DB_HOST}:{DB_PORT}) ---")
    if create_database():
        init_schema()
