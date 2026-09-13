import sqlite3
from datetime import datetime, timedelta

DB_PATH = "market.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            category TEXT,
            title TEXT,
            price INTEGER,
            description TEXT,
            photo_id TEXT,
            status TEXT DEFAULT 'pending',
            payment_id TEXT,
            paid INTEGER DEFAULT 0,
            created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            free_ads_used INTEGER DEFAULT 0,
            first_seen TEXT,
            last_seen TEXT
        )
    """)

    conn.commit()
    conn.close()

    # Переносим всех, кто подавал объявления, в таблицу users
    migrate_users_from_items()


def migrate_users_from_items():
    """Добавляет в users всех, кто уже подавал объявления."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT DISTINCT user_id FROM items WHERE user_id IS NOT NULL")
    user_ids = [r[0] for r in cur.fetchall()]

    now = datetime.now().isoformat()

    for uid in user_ids:
        cur.execute("SELECT user_id FROM users WHERE user_id = ?", (uid,))
        if cur.fetchone() is None:
            cur.execute(
                "INSERT INTO users (user_id, free_ads_used, first_seen, last_seen) VALUES (?, 0, ?, ?)",
                (uid, now, now)
            )

    conn.commit()
    conn.close()


def register_user(user_id):
    """Записывает пользователя при первом /start и обновляет last_seen."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    now = datetime.now().isoformat()

    cur.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    row = cur.fetchone()

    if row is None:
        cur.execute(
            "INSERT INTO users (user_id, free_ads_used, first_seen, last_seen) VALUES (?, 0, ?, ?)",
            (user_id, now, now)
        )
    else:
        cur.execute("UPDATE users SET last_seen = ? WHERE user_id = ?", (now, user_id))

    conn.commit()
    conn.close()


def update_last_seen(user_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE users SET last_seen = ? WHERE user_id = ?",
                (datetime.now().isoformat(), user_id))
    conn.commit()
    conn.close()


def add_item(user_id, username, category, title, price, description, photo_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO items
        (user_id, username, category, title, price, description, photo_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, username, category, title, price, description, photo_id,
          datetime.now().isoformat()))
    item_id = cur.lastrowid
    conn.commit()
    conn.close()
    return item_id


def get_item(item_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM items WHERE id = ?", (item_id,))
    row = cur.fetchone()
    conn.close()
    return row


def update_status(item_id, status):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE items SET status = ? WHERE id = ?", (status, item_id))
    conn.commit()
    conn.close()


def update_payment(item_id, payment_id, paid=0):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE items SET payment_id = ?, paid = ? WHERE id = ?",
                (payment_id, paid, item_id))
    conn.commit()
    conn.close()


def mark_paid(item_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE items SET paid = 1 WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()


def get_user_items(user_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, title, price, status FROM items
        WHERE user_id = ? ORDER BY id DESC
    """, (user_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_stats():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM items")
    total = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM items WHERE status = 'pending'")
    pending = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM items WHERE status = 'approved'")
    approved = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM items WHERE status = 'rejected'")
    rejected = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM users")
    users = cur.fetchone()[0]

    week_ago = (datetime.now() - timedelta(days=7)).isoformat()

    cur.execute("SELECT COUNT(*) FROM users WHERE first_seen >= ?", (week_ago,))
    new_week = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM users WHERE last_seen >= ?", (week_ago,))
    active_week = cur.fetchone()[0]

    conn.close()
    return {
        "total": total,
        "pending": pending,
        "approved": approved,
        "rejected": rejected,
        "users": users,
        "new_week": new_week,
        "active_week": active_week
    }


def get_pending_items():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, title, price FROM items
        WHERE status = 'pending' ORDER BY id ASC
    """)
    rows = cur.fetchall()
    conn.close()
    return rows


def get_all_user_ids():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM users")
    rows = cur.fetchall()
    conn.close()
    return [r[0] for r in rows]
