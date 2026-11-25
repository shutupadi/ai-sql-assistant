"""Natural-language question -> SQL.

Order of preference:
1. Approved SQL from the feedback table (same question got a thumbs up before).
2. OpenAI API, if OPENAI_API_KEY is set: prompt = schema + rules + approved examples + question.
3. Offline keyword rules (ai_sql/offline.py), so the demo works without a key.
"""
import os
import re

from ai_sql import feedback
from ai_sql.db import get_schema
from ai_sql.offline import offline_sql

MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

SYSTEM_PROMPT = """You are a SQL assistant for a retail company's SQLite database.
Write ONE SQLite SELECT query that answers the user's question.
Rules:
- Use only the tables and columns in the schema.
- Revenue never includes orders with status 'CANCELLED'.
- Product or category revenue = SUM(order_items.quantity * order_items.unit_price).
- Round money to 2 decimals. Use strftime('%Y-%m', order_date) for months.
- Return only the SQL, no explanation."""


def build_prompt(schema, question, examples=()):
    parts = [f"Schema:\n{schema}"]
    if examples:
        shots = "\n\n".join(f"Question: {q}\nSQL: {s}" for q, s in examples)
        parts.append(f"Examples of approved answers:\n{shots}")
    parts.append(f"Question: {question}\nSQL:")
    return "\n\n".join(parts)


def clean_sql(text):
    """LLMs often wrap SQL in ```sql ... ``` fences; strip them."""
    match = re.search(r"```(?:sql)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    return (match.group(1) if match else text).strip().rstrip(";").strip()


def openai_sql(conn, question, client):
    prompt = build_prompt(get_schema(conn), question, feedback.approved_examples(conn))
    response = client.chat.completions.create(
        model=MODEL,
        temperature=0,                                  # same question -> same answer
        messages=[{"role": "system", "content": SYSTEM_PROMPT},
                  {"role": "user", "content": prompt}])
    return clean_sql(response.choices[0].message.content)


def get_openai_client():
    if not os.getenv("OPENAI_API_KEY"):
        return None
    from openai import OpenAI                           # imported only when a key is set
    return OpenAI()                                     # reads OPENAI_API_KEY from the environment


def generate_sql(conn, question, client=None, use_feedback=True, mode="auto"):
    """Returns {"sql": ..., "source": "approved" | "openai" | "offline"}. sql is None if not understood.

    mode: "auto" (OpenAI if a key is set, else offline), "openai" or "offline".
    """
    if use_feedback:
        approved = feedback.find_approved(conn, question)
        if approved:
            return {"sql": approved, "source": "approved"}

    if mode != "offline":
        client = client or get_openai_client()
        if client is not None:
            return {"sql": openai_sql(conn, question, client), "source": "openai"}
        if mode == "openai":
            raise RuntimeError("OPENAI_API_KEY is not set")

    return {"sql": offline_sql(question), "source": "offline"}
