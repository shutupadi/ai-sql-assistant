"""Database helpers: connect, describe the schema, and run a query safely."""
import os
import re
import sqlite3
from pathlib import Path

import pandas as pd

DEFAULT_DB = Path(__file__).resolve().parent.parent / "data" / "retail.db"
BLOCKED = re.compile(r"\b(insert|update|delete|drop|alter|create|replace|attach|detach|pragma|vacuum)\b",
                     re.IGNORECASE)


def connect(path=None):
    path = path or os.getenv("RETAIL_DB", DEFAULT_DB)
    conn = sqlite3.connect(path, check_same_thread=False)   # Streamlit reruns on other threads
    return conn


def get_schema(conn):
    """Returns the CREATE TABLE statements. This is what we show the LLM so it knows the tables."""
    rows = conn.execute("SELECT sql FROM sqlite_master WHERE type = 'table' "
                        "AND name <> 'query_feedback' ORDER BY name").fetchall()
    return "\n\n".join(r[0] for r in rows)


def is_safe_select(sql):
    """Only a single read-only SELECT (or WITH ... SELECT) is allowed to run."""
    text = sql.strip().rstrip(";").strip()
    if not text:
        return False
    if ";" in text:                                     # more than one statement
        return False
    if not text.lower().startswith(("select", "with")):
        return False
    return not BLOCKED.search(text)


def run_query(conn, sql):
    if not is_safe_select(sql):
        raise ValueError("Only a single SELECT query is allowed.")
    return pd.read_sql_query(sql, conn)
