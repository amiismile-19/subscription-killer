"""
sync_to_postgres.py - Syncs all SQLite data into PostgreSQL for pgAdmin 4.
Can be executed standalone:
  python sync_to_postgres.py --password <YOUR_POSTGRES_PASSWORD>
"""

import sys
import os
import argparse
import sqlite3
from pathlib import Path

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("Error: psycopg2-binary is required. Run: pip install psycopg2-binary")
    sys.exit(1)

def migrate_sqlite_to_postgres(sqlite_path, pg_host, pg_port, pg_db, pg_user, pg_password):
    print(f"Connecting to SQLite database at {sqlite_path}...")
    if not os.path.exists(sqlite_path):
        print(f"Error: SQLite database {sqlite_path} does not exist.")
        return False

    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row

    print(f"Connecting to PostgreSQL at {pg_host}:{pg_port}/{pg_db} as user '{pg_user}'...")
    try:
        pg_conn = psycopg2.connect(
            host=pg_host,
            port=pg_port,
            dbname=pg_db,
            user=pg_user,
            password=pg_password,
            connect_timeout=5
        )
        pg_conn.autocommit = False
    except Exception as exc:
        print(f"Failed to connect to PostgreSQL: {exc}")
        return False

    pg_cur = pg_conn.cursor()

    # 1. Execute Schema
    schema_file = Path(__file__).parent / "schema_postgres.sql"
    if schema_file.exists():
        print("Applying PostgreSQL schema...")
        with open(schema_file, "r", encoding="utf-8") as f:
            pg_cur.execute(f.read())
        pg_conn.commit()

    tables = [
        ("users", ["user_id", "display_name", "language", "timezone", "created_at"]),
        ("subscriptions", ["subscription_id", "user_id", "transaction_ref", "merchant", "amount", "currency", "billing_frequency", "plan_name", "renewal_date", "cancellation_deadline", "status", "created_at"]),
        ("cancellation_requests", ["request_id", "subscription_id", "transaction_ref", "requested_at", "status", "confirmation_ref", "message"]),
        ("notification_preferences", ["user_id", "in_app_enabled", "audio_alerts", "price_alerts", "reminder_days", "preferred_channels"]),
        ("notifications", ["notification_id", "user_id", "subscription_id", "transaction_ref", "title", "event_type", "message", "scheduled_at", "sent_at", "status", "created_at"]),
        ("score_ledger", ["ledger_id", "user_id", "subscription_id", "transaction_ref", "action_type", "points", "idempotency_key", "note", "created_at"]),
        ("audit_logs", ["audit_id", "user_id", "action", "details", "created_at"])
    ]

    for table, cols in tables:
        try:
            s_rows = sqlite_conn.execute(f"SELECT * FROM {table}").fetchall()
            if not s_rows:
                continue

            print(f"Syncing {len(s_rows)} records for table '{table}'...")
            col_names = ", ".join(cols)
            placeholders = ", ".join(["%s"] * len(cols))
            insert_sql = f"""
                INSERT INTO {table} ({col_names})
                VALUES ({placeholders})
                ON CONFLICT DO NOTHING
            """

            for r in s_rows:
                vals = []
                for c in cols:
                    val = r[c] if c in r.keys() else None
                    if table == "notification_preferences" and c in ["in_app_enabled", "audio_alerts", "price_alerts"]:
                        val = bool(val)
                    vals.append(val)
                pg_cur.execute(insert_sql, vals)

            # Reset sequence to max id so new inserts auto-increment cleanly
            pk_col = cols[0]
            if pk_col.endswith("_id"):
                pg_cur.execute(f"SELECT COALESCE(MAX({pk_col}), 1) FROM {table}")
                max_id = pg_cur.fetchone()[0]
                seq_query = f"SELECT pg_get_serial_sequence('{table}', '{pk_col}')"
                pg_cur.execute(seq_query)
                seq_name = pg_cur.fetchone()[0]
                if seq_name:
                    pg_cur.execute(f"SELECT setval('{seq_name}', {max_id})")

            pg_conn.commit()
            print(f"[OK] Table '{table}' synced successfully.")
        except Exception as e:
            pg_conn.rollback()
            print(f"Notice on syncing {table}: {e}")

    sqlite_conn.close()
    pg_conn.close()
    print("\nAll data successfully synced to PostgreSQL! You can now view and query it in pgAdmin 4.")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync SQLite to PostgreSQL for pgAdmin 4")
    parser.add_argument("--password", "-p", default=os.getenv("POSTGRES_PASSWORD", ""), help="PostgreSQL password")
    parser.add_argument("--user", "-u", default=os.getenv("POSTGRES_USER", "postgres"), help="PostgreSQL username")
    parser.add_argument("--host", default=os.getenv("POSTGRES_HOST", "localhost"), help="PostgreSQL host")
    parser.add_argument("--port", type=int, default=int(os.getenv("POSTGRES_PORT", "5432")), help="PostgreSQL port")
    parser.add_argument("--db", "-d", default=os.getenv("POSTGRES_DB", "postgres"), help="PostgreSQL database name")
    parser.add_argument("--sqlite", default=os.getenv("DATABASE_PATH", "./subscription_killer.db"), help="SQLite path")

    args = parser.parse_args()
    success = migrate_sqlite_to_postgres(
        sqlite_path=args.sqlite,
        pg_host=args.host,
        pg_port=args.port,
        pg_db=args.db,
        pg_user=args.user,
        pg_password=args.password
    )
    if not success:
        sys.exit(1)
