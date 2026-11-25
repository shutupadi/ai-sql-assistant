import pytest

from ai_sql import feedback
from ai_sql.generator import generate_sql


def test_approved_sql_is_reused_for_same_question(conn):
    feedback.save_feedback(conn, "Revenue in Jaipur?", "SELECT 42 AS revenue", 1, source="offline")
    result = generate_sql(conn, "revenue in jaipur")    # case and punctuation don't matter
    assert result == {"sql": "SELECT 42 AS revenue", "source": "approved"}


def test_thumbs_down_is_not_reused(conn):
    feedback.save_feedback(conn, "Show monthly revenue", "SELECT 1", -1)
    assert generate_sql(conn, "Show monthly revenue")["source"] == "offline"


def test_invalid_rating_rejected(conn):
    with pytest.raises(ValueError):
        feedback.save_feedback(conn, "q", "SELECT 1", 5)


def test_stats_count_up_and_down_per_source(conn):
    feedback.save_feedback(conn, "a", "SELECT 1", 1, source="offline")
    feedback.save_feedback(conn, "b", "SELECT 1", -1, source="offline")
    feedback.save_feedback(conn, "c", "SELECT 1", 1, source="openai")
    assert sorted(feedback.feedback_stats(conn)) == [("offline", 1, 1), ("openai", 1, 0)]
