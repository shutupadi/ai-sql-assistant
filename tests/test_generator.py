from types import SimpleNamespace

import pytest

from ai_sql import feedback
from ai_sql.db import is_safe_select, run_query
from ai_sql.generator import clean_sql, generate_sql
from ai_sql.offline import offline_sql


class FakeOpenAI:
    """Stands in for the OpenAI client: records the prompt and returns a fixed answer."""

    def __init__(self, answer):
        self.answer, self.messages = answer, None
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, model, temperature, messages):
        self.messages = messages
        message = SimpleNamespace(content=self.answer)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def test_offline_uses_filters_from_question():
    sql = offline_sql("Top 10 customers in Delhi")
    assert "c.city = 'Delhi'" in sql and "LIMIT 10" in sql and "CANCELLED" in sql


def test_offline_returns_none_when_not_understood():
    assert offline_sql("What's the weather today?") is None


@pytest.mark.parametrize("question", ["Show monthly revenue", "Revenue by category",
                                      "Top 3 products by units sold", "Average order value in Pune"])
def test_offline_sql_runs(conn, question):
    assert len(run_query(conn, offline_sql(question))) > 0


@pytest.mark.parametrize("sql,ok", [
    ("SELECT * FROM orders", True),
    ("WITH x AS (SELECT 1) SELECT * FROM x;", True),
    ("DELETE FROM orders", False),
    ("SELECT 1; DROP TABLE orders", False),
    ("UPDATE orders SET status = 'X'", False),
    ("", False),
])
def test_only_single_select_allowed(sql, ok):
    assert is_safe_select(sql) is ok


def test_run_query_blocks_unsafe_sql(conn):
    with pytest.raises(ValueError):
        run_query(conn, "DROP TABLE orders")


def test_clean_sql_strips_markdown_fences():
    assert clean_sql("```sql\nSELECT 1;\n```") == "SELECT 1"


def test_openai_prompt_contains_schema_and_approved_examples(conn):
    feedback.save_feedback(conn, "How many products?", "SELECT COUNT(*) FROM products", 1)
    client = FakeOpenAI("```sql\nSELECT COUNT(*) FROM customers\n```")
    result = generate_sql(conn, "How many customers?", client=client)
    prompt = client.messages[1]["content"]
    assert result == {"sql": "SELECT COUNT(*) FROM customers", "source": "openai"}
    assert "CREATE TABLE orders" in prompt
    assert "How many products?" in prompt               # feedback loop -> few-shot example


def test_falls_back_to_offline_without_key(conn):
    assert generate_sql(conn, "Show monthly revenue")["source"] == "offline"


def test_openai_mode_without_key_raises(conn):
    with pytest.raises(RuntimeError):
        generate_sql(conn, "Show monthly revenue", mode="openai")
