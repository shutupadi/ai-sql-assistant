"""Feedback loop: thumbs up / down are saved to the query_feedback table.

How the feedback is used:
1. A question that was approved (thumbs up) before is answered with the approved SQL straight away.
2. The latest approved examples are added to the LLM prompt (few-shot), so answers improve over time.
3. Thumbs-down answers are counted per source, so we can see where the generator is weak.
"""
import re
from datetime import datetime


def normalise(question):
    return re.sub(r"[^a-z0-9 ]", "", question.lower()).strip()


def save_feedback(conn, question, sql, rating, comment="", source=""):
    if rating not in (1, -1):
        raise ValueError("rating must be 1 (good) or -1 (bad)")
    conn.execute("INSERT INTO query_feedback (question, sql, rating, comment, source, created_at) "
                 "VALUES (?, ?, ?, ?, ?, ?)",
                 (question, sql, rating, comment, source, datetime.now().isoformat(timespec="seconds")))
    conn.commit()


def find_approved(conn, question):
    """SQL from the latest thumbs-up for the same question, if there is one."""
    key = normalise(question)
    rows = conn.execute("SELECT question, sql FROM query_feedback WHERE rating = 1 "
                        "ORDER BY feedback_id DESC").fetchall()
    return next((sql for q, sql in rows if normalise(q) == key), None)


def approved_examples(conn, limit=5):
    return conn.execute("SELECT question, sql FROM query_feedback WHERE rating = 1 "
                        "ORDER BY feedback_id DESC LIMIT ?", (limit,)).fetchall()


def feedback_stats(conn):
    """Thumbs up / down per source (openai, offline, approved)."""
    return conn.execute("SELECT source, SUM(rating = 1) AS thumbs_up, SUM(rating = -1) AS thumbs_down "
                        "FROM query_feedback GROUP BY source").fetchall()
