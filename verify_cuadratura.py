from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()
DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')
DATABASE_URL = f'postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    r = conn.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name='expense_ledger' AND column_name='sede'"
    ))
    row = r.fetchone()
    if not row:
        conn.execute(text('ALTER TABLE expense_ledger ADD COLUMN IF NOT EXISTS sede VARCHAR(50)'))
        conn.commit()
        print('columna sede agregada a expense_ledger')
    else:
        print('columna sede ya existe')

    r2 = conn.execute(text('SELECT COUNT(*) FROM raw_bank WHERE amount < 0'))
    print(f'raw_bank egresos: {r2.fetchone()[0]}')

    r3 = conn.execute(text("SELECT COUNT(*) FROM expense_ledger WHERE status = 'PAID_VERIFIED'"))
    print(f'expense_ledger PAID_VERIFIED: {r3.fetchone()[0]}')

    r4 = conn.execute(text(
        'SELECT ec.name, COUNT(el.uuid), SUM(el.amount_due) '
        'FROM expense_ledger el '
        'LEFT JOIN expense_categories ec ON ec.id = el.category_id '
        'GROUP BY ec.name ORDER BY SUM(el.amount_due) DESC'
    ))
    print('\nEgresos por categoria:')
    for row in r4.fetchall():
        print(f'  {row[0]}: {row[1]} registros  ${row[2]:,.0f}')
