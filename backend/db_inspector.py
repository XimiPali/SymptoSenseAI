"""
db_inspector.py
---------------
Read-only debugging tool for inspecting the healthcare_ai MySQL database.

Usage:
    python backend/db_inspector.py
"""

import os
import sys

# Allow imports from the backend directory (e.g. database.py)
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
import mysql.connector

load_dotenv()

# ── Connection ────────────────────────────────────────────────────────────────

def _get_connection():
    """Return a raw mysql.connector connection using the same env vars as database.py."""
    database_url = os.getenv(
        "DATABASE_URL",
        "mysql+mysqlconnector://root:password@localhost:3306/healthcare_ai",
    )
    # Parse  mysql+mysqlconnector://user:pass@host:port/dbname
    rest = database_url.split("://", 1)[1]          # user:pass@host:port/dbname
    userinfo, hostinfo = rest.rsplit("@", 1)
    user, password = userinfo.split(":", 1)
    host_port, database = hostinfo.split("/", 1)
    if ":" in host_port:
        host, port = host_port.split(":", 1)
        port = int(port)
    else:
        host, port = host_port, 3306

    return mysql.connector.connect(
        host=host, port=port, user=user, password=password, database=database
    )


# ── Formatting helpers ────────────────────────────────────────────────────────

def _print_table(title, columns, rows):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")
    if not rows:
        print("  (no records found)")
        return

    col_widths = [len(c) for c in columns]
    for row in rows:
        for i, val in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(val)))

    fmt = "  " + "  |  ".join(f"{{:<{w}}}" for w in col_widths)
    sep = "  " + "--+--".join("-" * w for w in col_widths)

    print(fmt.format(*columns))
    print(sep)
    for row in rows:
        print(fmt.format(*[str(v) for v in row]))
    print(f"\n  {len(rows)} row(s)")


# ── Inspector functions ───────────────────────────────────────────────────────

def show_tables():
    """List all tables in the database."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("SHOW TABLES;")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    _print_table("TABLES IN DATABASE", ["Table Name"], rows)


def show_indexes():
    """List indexes for each table."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("SHOW TABLES;")
    tables = [r[0] for r in cursor.fetchall()]

    for table in tables:
        cursor.execute(f"SHOW INDEX FROM `{table}`;")
        cols = [d[0] for d in cursor.description]
        rows = cursor.fetchall()
        _print_table(f"INDEXES  --  {table}", cols, rows)

    cursor.close()
    conn.close()


def show_users():
    """Print all registered users (password hash hidden)."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, username, email, age, gender, is_active, created_at FROM users;"
    )
    cols = [d[0] for d in cursor.description]
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    _print_table("USERS", cols, rows)


def show_predictions(limit=None):
    """Print prediction records. Pass limit to restrict the number of rows."""
    conn = _get_connection()
    cursor = conn.cursor()
    sql = (
        "SELECT id, user_id, predicted_disease, confidence, "
        "age_at_prediction, gender_at_prediction, created_at "
        "FROM predictions ORDER BY created_at DESC"
    )
    if limit:
        sql += f" LIMIT {int(limit)}"
    sql += ";"
    cursor.execute(sql)
    cols = [d[0] for d in cursor.description]
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    title = f"PREDICTIONS (last {limit})" if limit else "PREDICTIONS (all)"
    _print_table(title, cols, rows)


def show_symptom_history():
    """Print the symptoms_input JSON for every prediction, joined with the username."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT p.id, u.username, p.symptoms_input, p.created_at
        FROM predictions p
        JOIN users u ON u.id = p.user_id
        ORDER BY p.created_at DESC;
        """
    )
    cols = [d[0] for d in cursor.description]
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    _print_table("SYMPTOM HISTORY", cols, rows)


def show_diseases(limit=20):
    """Print diseases stored in the database."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT id, name, created_at FROM diseases LIMIT {int(limit)};")
    cols = [d[0] for d in cursor.description]
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    _print_table(f"DISEASES (first {limit})", cols, rows)


def show_symptoms(limit=30):
    """Print symptoms stored in the database."""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"SELECT id, name, weight, created_at FROM symptoms LIMIT {int(limit)};"
    )
    cols = [d[0] for d in cursor.description]
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    _print_table(f"SYMPTOMS (first {limit})", cols, rows)


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    print("\n" + "#" * 60)
    print("#  SymptoSenseAI  --  Database Inspector")
    print("#" * 60)

    show_tables()
    show_users()
    show_predictions()          # all predictions
    show_predictions(limit=10)  # most recent 10
    show_symptom_history()
    show_diseases()
    show_symptoms()
    show_indexes()

    print("\n" + "#" * 60)
    print("#  Inspection complete")
    print("#" * 60 + "\n")


if __name__ == "__main__":
    main()
