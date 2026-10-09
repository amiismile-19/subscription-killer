import os
from pathlib import Path
from flask import current_app, g

POSTGRES_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  user_id BIGSERIAL PRIMARY KEY,
  display_name TEXT NOT NULL DEFAULT 'Demo User',
  language TEXT NOT NULL DEFAULT 'en',
  timezone TEXT NOT NULL DEFAULT 'Asia/Kolkata',
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS subscriptions (
  subscription_id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  transaction_ref TEXT NOT NULL,
  merchant TEXT NOT NULL,
  amount NUMERIC(12,2) NOT NULL CHECK(amount >= 0),
  currency TEXT NOT NULL DEFAULT 'INR',
  billing_frequency TEXT NOT NULL DEFAULT 'monthly',
  renewal_date DATE,
  cancellation_deadline DATE,
  status TEXT NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(user_id, merchant, transaction_ref)
);
CREATE TABLE IF NOT EXISTS cancellation_requests (
  request_id BIGSERIAL PRIMARY KEY,
  subscription_id BIGINT NOT NULL REFERENCES subscriptions(subscription_id) ON DELETE CASCADE,
  requested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
  status TEXT NOT NULL DEFAULT 'pending',
  confirmation_ref TEXT,
  message TEXT
);
CREATE TABLE IF NOT EXISTS notification_preferences (
  user_id BIGINT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
  in_app_enabled BOOLEAN NOT NULL DEFAULT TRUE,
  reminder_days TEXT NOT NULL DEFAULT '7,3,1',
  price_alerts BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE TABLE IF NOT EXISTS notifications (
  notification_id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  subscription_id BIGINT REFERENCES subscriptions(subscription_id) ON DELETE CASCADE,
  event_type TEXT NOT NULL,
  message TEXT NOT NULL,
  scheduled_at TIMESTAMPTZ NOT NULL,
  sent_at TIMESTAMPTZ,
  status TEXT NOT NULL DEFAULT 'scheduled',
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS score_ledger (
  ledger_id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  subscription_id BIGINT REFERENCES subscriptions(subscription_id) ON DELETE SET NULL,
  action_type TEXT NOT NULL,
  points INTEGER NOT NULL,
  idempotency_key TEXT NOT NULL UNIQUE,
  note TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS audit_logs (
  audit_id BIGSERIAL PRIMARY KEY,
  user_id BIGINT,
  action TEXT NOT NULL,
  details TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

class CursorResult:
    """Small wrapper so route code can use fetchone/fetchall and row dictionaries."""
    def __init__(self, cursor):
        self.cursor = cursor
        self.lastrowid = None

    def fetchone(self):
        return self.cursor.fetchone()

    def fetchall(self):
        return self.cursor.fetchall()

    @property
    def rowcount(self):
        return self.cursor.rowcount

class PostgresConnection:
    def __init__(self, conn):
        self.conn = conn

    def execute(self, sql, params=()):
        # Project SQL uses qmark placeholders; psycopg uses %s placeholders.
        sql = sql.replace("?", "%s")
        cur = self.conn.cursor()
        cur.execute(sql, params)
        return CursorResult(cur)

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()

def get_db():
    if "db" not in g:
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise RuntimeError("Install dependencies with: pip install -r requirements.txt") from exc
        database_url = current_app.config["DATABASE_URL"]
        if not database_url:
            raise RuntimeError(
                "DATABASE_URL is not set. Add it to your environment, for example "
                "postgresql://postgres:password@localhost:5432/subscription_killer"
            )
        conn = psycopg.connect(database_url, row_factory=dict_row)
        g.db = PostgresConnection(conn)
    return g.db

def close_db(_exc=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()

def init_db(database_url=None):
    """Create tables and seed the demo user if the database is empty."""
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:
        raise RuntimeError("Install dependencies with: pip install -r requirements.txt") from exc
    database_url = database_url or os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/subscription_killer")
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(POSTGRES_SCHEMA)
            cur.execute("SELECT COUNT(*) AS n FROM users")
            if cur.fetchone()["n"] == 0:
                cur.execute(
                    "INSERT INTO users(display_name, language, timezone) VALUES (%s, %s, %s) RETURNING user_id",
                    ("Demo User", "en", "Asia/Kolkata")
                )
                user_id = cur.fetchone()["user_id"]
                cur.execute(
                    "INSERT INTO notification_preferences(user_id) VALUES (%s) ON CONFLICT(user_id) DO NOTHING",
                    (user_id,)
                )
        conn.commit()
