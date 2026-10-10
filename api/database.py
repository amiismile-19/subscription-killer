import os
import re
import sqlite3
from pathlib import Path
from flask import current_app, g

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
  user_id INTEGER PRIMARY KEY AUTOINCREMENT,
  display_name TEXT NOT NULL DEFAULT 'Demo User',
  language TEXT NOT NULL DEFAULT 'en',
  timezone TEXT NOT NULL DEFAULT 'Asia/Kolkata',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS subscriptions (
  subscription_id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  transaction_ref TEXT NOT NULL,
  merchant TEXT NOT NULL,
  amount REAL NOT NULL CHECK(amount >= 0),
  currency TEXT NOT NULL DEFAULT 'INR',
  billing_frequency TEXT NOT NULL DEFAULT 'monthly',
  plan_name TEXT NOT NULL DEFAULT 'Standard',
  renewal_date TEXT,
  cancellation_deadline TEXT,
  status TEXT NOT NULL DEFAULT 'active',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(user_id, merchant, transaction_ref)
);

CREATE TABLE IF NOT EXISTS cancellation_requests (
  request_id INTEGER PRIMARY KEY AUTOINCREMENT,
  subscription_id INTEGER NOT NULL REFERENCES subscriptions(subscription_id) ON DELETE CASCADE,
  transaction_ref TEXT,
  requested_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  status TEXT NOT NULL DEFAULT 'cancelled',
  confirmation_ref TEXT,
  message TEXT
);

CREATE TABLE IF NOT EXISTS notification_preferences (
  user_id INTEGER PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
  in_app_enabled INTEGER NOT NULL DEFAULT 1,
  audio_alerts INTEGER NOT NULL DEFAULT 1,
  price_alerts INTEGER NOT NULL DEFAULT 1,
  reminder_days TEXT NOT NULL DEFAULT '7,3,1',
  preferred_channels TEXT NOT NULL DEFAULT 'in_app,audio'
);

CREATE TABLE IF NOT EXISTS notifications (
  notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  subscription_id INTEGER REFERENCES subscriptions(subscription_id) ON DELETE CASCADE,
  transaction_ref TEXT,
  title TEXT NOT NULL DEFAULT 'Subscription Alert',
  event_type TEXT NOT NULL,
  message TEXT NOT NULL,
  scheduled_at TEXT NOT NULL,
  sent_at TEXT,
  status TEXT NOT NULL DEFAULT 'scheduled',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS score_ledger (
  ledger_id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  subscription_id INTEGER REFERENCES subscriptions(subscription_id) ON DELETE SET NULL,
  transaction_ref TEXT,
  action_type TEXT NOT NULL,
  points INTEGER NOT NULL,
  idempotency_key TEXT NOT NULL UNIQUE,
  note TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_logs (
  audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER,
  action TEXT NOT NULL,
  details TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

TABLE_PRIMARY_KEYS = {
    "subscriptions": "subscription_id",
    "cancellation_requests": "request_id",
    "notifications": "notification_id",
    "score_ledger": "ledger_id",
    "audit_logs": "audit_id",
    "users": "user_id",
    "notification_preferences": "user_id",
}

class PostgresCursorWrapper:
    def __init__(self, cur, lastrowid=None):
        self._cur = cur
        self.lastrowid = lastrowid

    @property
    def rowcount(self):
        return self._cur.rowcount

    def fetchone(self):
        row = self._cur.fetchone()
        return dict(row) if row is not None else None

    def fetchall(self):
        rows = self._cur.fetchall()
        return [dict(r) for r in rows]

    def __iter__(self):
        for row in self._cur:
            yield dict(row)

class PostgresConnectionWrapper:
    def __init__(self, conn):
        self.conn = conn

    def execute(self, query, params=None):
        cleaned_query = query.strip()
        # Handle SQLite 'INSERT OR IGNORE INTO' -> PostgreSQL 'INSERT INTO ... ON CONFLICT DO NOTHING'
        if re.search(r"INSERT\s+OR\s+IGNORE\s+INTO", cleaned_query, re.IGNORECASE):
            cleaned_query = re.sub(r"INSERT\s+OR\s+IGNORE\s+INTO", "INSERT INTO", cleaned_query, flags=re.IGNORECASE)
            if "ON CONFLICT" not in cleaned_query.upper():
                cleaned_query += " ON CONFLICT DO NOTHING"

        # Translate '?' placeholders to '%s'
        pg_query = cleaned_query.replace("?", "%s")

        # Detect INSERT without RETURNING for lastrowid
        last_id = None
        is_insert = pg_query.strip().upper().startswith("INSERT INTO")
        if is_insert and "RETURNING" not in pg_query.upper():
            match = re.search(r"INSERT\s+INTO\s+([a-zA-Z0-9_]+)", pg_query, re.IGNORECASE)
            if match:
                tbl = match.group(1).lower()
                pk = TABLE_PRIMARY_KEYS.get(tbl)
                if pk:
                    pg_query_with_ret = f"{pg_query} RETURNING {pk}"
                    cur = self.conn.cursor(cursor_factory=RealDictCursor)
                    try:
                        cur.execute(pg_query_with_ret, params)
                        ret_row = cur.fetchone()
                        if ret_row:
                            last_id = ret_row.get(pk)
                        return PostgresCursorWrapper(cur, lastrowid=last_id)
                    except Exception:
                        self.conn.rollback()

        cur = self.conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(pg_query, params)
        return PostgresCursorWrapper(cur, lastrowid=last_id)

    def executemany(self, query, seq_of_params):
        pg_query = query.replace("?", "%s")
        cur = self.conn.cursor(cursor_factory=RealDictCursor)
        cur.executemany(pg_query, seq_of_params)
        return PostgresCursorWrapper(cur)

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()

def get_db():
    if "db" not in g:
        # Check if PostgreSQL is enabled and configured
        db_type = current_app.config.get("DATABASE_TYPE", "auto")
        pg_pwd = current_app.config.get("POSTGRES_PASSWORD", "")
        pg_host = current_app.config.get("POSTGRES_HOST", "localhost")
        pg_port = current_app.config.get("POSTGRES_PORT", 5432)
        pg_db = current_app.config.get("POSTGRES_DB", "postgres")
        pg_user = current_app.config.get("POSTGRES_USER", "postgres")

        use_pg = False
        if PSYCOPG2_AVAILABLE and (db_type == "postgres" or (db_type == "auto" and pg_pwd)):
            try:
                pg_conn = psycopg2.connect(
                    host=pg_host,
                    port=pg_port,
                    dbname=pg_db,
                    user=pg_user,
                    password=pg_pwd,
                    connect_timeout=3
                )
                g.db = PostgresConnectionWrapper(pg_conn)
                g.db_type = "postgres"
                use_pg = True
            except Exception as e:
                current_app.logger.warning(f"PostgreSQL connection fallback to SQLite: {e}")

        if not use_pg:
            db_path = current_app.config["DATABASE_PATH"]
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            g.db = conn
            g.db_type = "sqlite"

    return g.db

def close_db(_exc=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()

def init_db(db_path):
    # Initialize SQLite database
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)

    # Migrate columns if upgrading existing database
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(subscriptions)")
    sub_cols = [c[1] for c in cur.fetchall()]
    if "plan_name" not in sub_cols:
        conn.execute("ALTER TABLE subscriptions ADD COLUMN plan_name TEXT NOT NULL DEFAULT 'Standard'")

    cur.execute("PRAGMA table_info(cancellation_requests)")
    cancel_cols = [c[1] for c in cur.fetchall()]
    if "transaction_ref" not in cancel_cols:
        conn.execute("ALTER TABLE cancellation_requests ADD COLUMN transaction_ref TEXT")

    cur.execute("PRAGMA table_info(notification_preferences)")
    pref_cols = [c[1] for c in cur.fetchall()]
    if "audio_alerts" not in pref_cols:
        conn.execute("ALTER TABLE notification_preferences ADD COLUMN audio_alerts INTEGER NOT NULL DEFAULT 1")
    if "preferred_channels" not in pref_cols:
        conn.execute("ALTER TABLE notification_preferences ADD COLUMN preferred_channels TEXT NOT NULL DEFAULT 'in_app,audio'")

    cur.execute("PRAGMA table_info(notifications)")
    notif_cols = [c[1] for c in cur.fetchall()]
    if "title" not in notif_cols:
        conn.execute("ALTER TABLE notifications ADD COLUMN title TEXT NOT NULL DEFAULT 'Subscription Alert'")
    if "transaction_ref" not in notif_cols:
        conn.execute("ALTER TABLE notifications ADD COLUMN transaction_ref TEXT")

    cur.execute("PRAGMA table_info(score_ledger)")
    score_cols = [c[1] for c in cur.fetchall()]
    if "transaction_ref" not in score_cols:
        conn.execute("ALTER TABLE score_ledger ADD COLUMN transaction_ref TEXT")

    # Seed demo user if no users exist
    if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        conn.execute(
            "INSERT INTO users(display_name, language, timezone) VALUES (?, ?, ?)",
            ("Demo User", "en", "Asia/Kolkata")
        )
        conn.execute("INSERT OR IGNORE INTO notification_preferences(user_id) VALUES (1)")

    # Seed starter demo subscriptions with transaction IDs (no bank details!) if empty
    if conn.execute("SELECT COUNT(*) FROM subscriptions").fetchone()[0] == 0:
        seed_data = [
            (1, "TXN-NTFLX-8921", "Netflix Premium", 649.0, "INR", "monthly", "4K Ultra HD", "2026-10-25", "2026-10-23", "active"),
            (1, "TXN-OPENAI-4412", "ChatGPT Plus", 1999.0, "INR", "monthly", "Plus", "2026-10-28", "2026-10-26", "active"),
            (1, "TXN-SPOT-7731", "Spotify Duo", 149.0, "INR", "monthly", "Premium Duo", "2026-11-04", "2026-11-02", "active"),
            (1, "TXN-AMZN-2384", "Amazon Prime", 1499.0, "INR", "yearly", "Annual Prime", "2027-01-15", "2027-01-13", "active"),
            (1, "TXN-YTBE-9102", "YouTube Premium", 149.0, "INR", "monthly", "Individual", "2026-10-21", "2026-10-19", "active"),
            (1, "TXN-CULT-5519", "Cult.fit Live", 1250.0, "INR", "monthly", "Live Workout", "2026-10-29", "2026-10-27", "active"),
        ]
        conn.executemany(
            """INSERT INTO subscriptions
               (user_id, transaction_ref, merchant, amount, currency, billing_frequency,
                plan_name, renewal_date, cancellation_deadline, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            seed_data
        )
        # Seed initial base financial health points
        conn.execute(
            """INSERT OR IGNORE INTO score_ledger
               (user_id, subscription_id, transaction_ref, action_type, points, idempotency_key, note)
               VALUES (1, NULL, 'TXN-GENESIS-INIT', 'baseline_onboarding', 30, 'genesis-init-1', 'Initial baseline financial credit score')"""
        )

    conn.commit()
    conn.close()