# %% [markdown]
# # SymptoSenseAI — Database Notebook
# Run each cell independently with the **Run Cell** button (or `Shift+Enter`).
# Requires: `pip install pandas mysql-connector-python python-dotenv`

# ──────────────────────────────────────────────────────────────────────────────
# CELL 1 — Database Connection
# ──────────────────────────────────────────────────────────────────────────────
# %%
import os
import sys
import pandas as pd
import mysql.connector
from dotenv import load_dotenv
from urllib.parse import unquote

# Resolve the backend directory regardless of where VS Code runs the cell from
_backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _backend_dir)

# Explicitly load backend/.env so credentials are always found
load_dotenv(os.path.join(_backend_dir, ".env"))

def _get_conn():
    url = os.getenv(
        "DATABASE_URL",
        "mysql+mysqlconnector://root:password@localhost:3306/healthcare_ai",
    )

    rest = url.split("://", 1)[1]
    userinfo, tail = rest.rsplit("@", 1)

    user, password = userinfo.split(":", 1)
    password = unquote(password)   # decode %21 -> !

    host_port, db = tail.split("/", 1)
    host, port = (host_port.split(":", 1) if ":" in host_port else (host_port, "3306"))

    return mysql.connector.connect(
        host=host,
        port=int(port),
        user=user,
        password=password,
        database=db,
    )

conn = _get_conn()
print(f"Connected to: {conn.server_host}  /  database: healthcare_ai")


# ──────────────────────────────────────────────────────────────────────────────
# CELL 2 — Show Tables
# ──────────────────────────────────────────────────────────────────────────────
# %%
df_tables = pd.read_sql("SHOW TABLES;", conn)
df_tables.columns = ["Table Name"]
print("=== TABLES IN DATABASE ===")
df_tables


# ──────────────────────────────────────────────────────────────────────────────
# CELL 3 — Show Table Schema (DESCRIBE)
# ──────────────────────────────────────────────────────────────────────────────
# %%
for table in df_tables["Table Name"]:
    print(f"\n--- DESCRIBE {table} ---")
    df = pd.read_sql(f"DESCRIBE `{table}`;", conn)
    print(df.to_string(index=False))


# ──────────────────────────────────────────────────────────────────────────────
# CELL 4 — Show Users
# ──────────────────────────────────────────────────────────────────────────────
# %%
df_users = pd.read_sql(
    """
    SELECT id, username, email, age, gender, is_active, created_at
    FROM users
    ORDER BY id;
    """,
    conn,
)
print(f"=== USERS  ({len(df_users)} rows) ===")
df_users


# ──────────────────────────────────────────────────────────────────────────────
# CELL 5 — Show Predictions (all, newest first)
# ──────────────────────────────────────────────────────────────────────────────
# %%
df_predictions = pd.read_sql(
    """
    SELECT id, user_id, predicted_disease, confidence,
           age_at_prediction, gender_at_prediction, created_at
    FROM predictions
    ORDER BY created_at DESC;
    """,
    conn,
)
print(f"=== PREDICTIONS  ({len(df_predictions)} rows) ===")
df_predictions


# ──────────────────────────────────────────────────────────────────────────────
# CELL 6 — Show Symptom Inputs
# ──────────────────────────────────────────────────────────────────────────────
# %%
df_symptoms = pd.read_sql(
    """
    SELECT p.id, u.username, p.user_id,
           p.symptoms_input, p.predicted_disease, p.confidence,
           p.created_at
    FROM predictions p
    JOIN users u ON u.id = p.user_id
    ORDER BY p.created_at DESC;
    """,
    conn,
)
print(f"=== SYMPTOM INPUTS  ({len(df_symptoms)} rows) ===")
df_symptoms


# ──────────────────────────────────────────────────────────────────────────────
# CELL 7 — Show Indexes
# ──────────────────────────────────────────────────────────────────────────────
# %%
for table in df_tables["Table Name"]:
    print(f"\n--- INDEXES: {table} ---")
    df = pd.read_sql(f"SHOW INDEX FROM `{table}`;", conn)
    keep = ["Table", "Key_name", "Column_name", "Non_unique", "Index_type"]
    print(df[[c for c in keep if c in df.columns]].to_string(index=False))


# ──────────────────────────────────────────────────────────────────────────────
# CELL 8 — Close Connection
# ──────────────────────────────────────────────────────────────────────────────
# %%
conn.close()
print("Connection closed.")
