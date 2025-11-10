import sys, os
import sqlite3
from pathlib import Path
from datetime import datetime

def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


DB_PATH = resource_path("data/finance.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        icon_path TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        amount REAL NOT NULL,
        type TEXT NOT NULL, -- 'income' or 'expense'
        category_id INTEGER,
        note TEXT,
        FOREIGN KEY(category_id) REFERENCES categories(id)
    )
    """,
]


def get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    for s in SCHEMA:
        cur.execute(s)
    conn.commit()
    conn.close()

# очистка бд

def clear_database():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM transactions")
    cur.execute("DELETE FROM categories")
    conn.commit()
    conn.close()

# категории

def add_category(name, icon_path=None):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO categories (name, icon_path) VALUES (?,?)", (name, icon_path))
        conn.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError:
        # в случае если уже существует
        return None
    finally:
        conn.close()

# def add_category(name, icon=None):
#     import sqlite3
#     conn = sqlite3.connect(DB_PATH)
#     cur = conn.cursor()
#     cur.execute("INSERT INTO categories (name, icon) VALUES (?, ?)", (name, icon))
#     conn.commit()
#     cid = cur.lastrowid
#     conn.close()
#     return cid

def get_categories():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM categories ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_category(cat_id, name, icon_path):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE categories SET name=?, icon_path=? WHERE id=?", (name, icon_path, cat_id))
    conn.commit()
    conn.close()


def delete_category(cat_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE transactions SET category_id=NULL WHERE category_id=?", (cat_id,))
    cur.execute("DELETE FROM categories WHERE id=?", (cat_id,))
    conn.commit()
    conn.close()


# транзакции

def add_transaction(date: str, amount: float, ttype: str, category_id: int = None, note: str = ''):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO transactions (date, amount, type, category_id, note) VALUES (?,?,?,?,?)",
        (date, amount, ttype, category_id, note)
    )
    conn.commit()
    tid = cur.lastrowid
    conn.close()
    return tid


def update_transaction(tid, date, amount, ttype, category_id, note):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE transactions SET date=?, amount=?, type=?, category_id=?, note=? WHERE id=?",
        (date, amount, ttype, category_id, note, tid)
    )
    conn.commit()
    conn.close()


def delete_transaction(tid):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM transactions WHERE id=?", (tid,))
    conn.commit()
    conn.close()


def clear_transactions():
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM transactions")
    conn.commit()
    conn.close()


def get_transactions(limit=None):
    conn = get_conn()
    cur = conn.cursor()
    q = "SELECT t.*, c.name as category_name, c.icon_path as category_icon FROM transactions t LEFT JOIN categories c ON t.category_id=c.id ORDER BY date DESC"
    if limit:
        q += f" LIMIT {int(limit)}"
    cur.execute(q)
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_balance():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT SUM(CASE WHEN type='Доход' THEN amount WHEN type='Трата' THEN -amount ELSE 0 END) as balance FROM transactions")
    r = cur.fetchone()
    conn.close()
    return r['balance'] if r and r['balance'] is not None else 0.0


def get_expenses_by_category():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT c.name, SUM(t.amount) as total FROM transactions t JOIN categories c ON t.category_id=c.id WHERE t.type='Трата' GROUP BY c.id ORDER BY total DESC"
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]