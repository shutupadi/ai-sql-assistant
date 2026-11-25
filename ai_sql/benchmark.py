"""Benchmark: generated SQL vs hand-written SQL.

A generated query counts as correct when it returns the same result set as the hand-written query
(same rows, values rounded to 2 decimals, row order and column names ignored). Comparing results,
not SQL text, is fair: there are many correct ways to write the same query.
"""
import time

from ai_sql.db import is_safe_select, run_query
from ai_sql.generator import generate_sql

NOT_CANCELLED = "status <> 'CANCELLED'"

# (business question, hand-written reference SQL)
BENCHMARK = [
    ("What is the total revenue?",
     f"SELECT ROUND(SUM(total_amount), 2) FROM orders WHERE {NOT_CANCELLED}"),
    ("How many orders were cancelled?",
     "SELECT COUNT(*) FROM orders WHERE status = 'CANCELLED'"),
    ("How many customers are in Mumbai?",
     "SELECT COUNT(*) FROM customers WHERE city = 'Mumbai'"),
    ("Show revenue by category",
     "SELECT p.category, ROUND(SUM(oi.quantity * oi.unit_price), 2) "
     "FROM order_items oi JOIN orders o USING (order_id) JOIN products p USING (product_id) "
     f"WHERE o.{NOT_CANCELLED} GROUP BY p.category"),
    ("Show monthly revenue",
     "WITH m AS (SELECT substr(order_date, 1, 7) AS month, total_amount FROM orders "
     f"WHERE {NOT_CANCELLED}) SELECT month, ROUND(SUM(total_amount), 2) FROM m GROUP BY month"),
    ("Who are the top 5 customers by spend?",
     "SELECT c.name, c.city, COUNT(*), ROUND(SUM(o.total_amount), 2) AS spend "
     f"FROM orders o JOIN customers c USING (customer_id) WHERE o.{NOT_CANCELLED} "
     "GROUP BY c.customer_id ORDER BY spend DESC LIMIT 5"),
    ("What are the top 3 electronics products by revenue?",
     "SELECT p.name, p.category, ROUND(SUM(oi.quantity * oi.unit_price), 2) AS rev "
     "FROM order_items oi JOIN orders o USING (order_id) JOIN products p USING (product_id) "
     f"WHERE o.{NOT_CANCELLED} AND p.category = 'Electronics' "
     "GROUP BY p.product_id ORDER BY rev DESC LIMIT 3"),
    ("Which products are low on stock?",
     "SELECT p.name, p.category, i.quantity_on_hand, i.reorder_level "
     "FROM products p JOIN inventory i USING (product_id) WHERE i.quantity_on_hand <= i.reorder_level"),
    ("How many orders are in each status?",
     "SELECT status, COUNT(*) FROM orders GROUP BY status"),
    ("Which city has the highest average order value?",
     "SELECT c.city, ROUND(AVG(o.total_amount), 2) AS aov FROM orders o JOIN customers c "
     f"USING (customer_id) WHERE o.{NOT_CANCELLED} GROUP BY c.city ORDER BY aov DESC LIMIT 1"),
]


def _normalise(df):
    """DataFrame -> sorted list of row tuples with floats rounded, so order and names don't matter."""
    rows = []
    for row in df.itertuples(index=False):
        rows.append(tuple(round(v, 2) if isinstance(v, float) else v for v in row))
    return sorted(rows, key=repr)


def results_match(df_a, df_b):
    return df_a.shape == df_b.shape and _normalise(df_a) == _normalise(df_b)


def evaluate(conn, question, generated_sql, reference_sql):
    """One benchmark row: did the generated SQL return the same answer as the reference?"""
    expected = run_query(conn, reference_sql)
    row = {"question": question, "generated_sql": generated_sql, "correct": False, "error": ""}
    if not generated_sql:
        row["error"] = "no SQL generated"
    elif not is_safe_select(generated_sql):
        row["error"] = "not a safe SELECT"
    else:
        try:
            row["correct"] = results_match(run_query(conn, generated_sql), expected)
        except Exception as exc:                        # invalid SQL counts as wrong, not a crash
            row["error"] = str(exc)
    return row


def run_benchmark(conn, mode="auto", client=None, cases=BENCHMARK):
    """Generates SQL for every benchmark question and scores it. Feedback is NOT used (fair test)."""
    rows, source = [], mode
    for question, reference in cases:
        start = time.perf_counter()
        result = generate_sql(conn, question, client=client, use_feedback=False, mode=mode)
        source = result["source"]
        row = evaluate(conn, question, result["sql"], reference)
        row["seconds"] = round(time.perf_counter() - start, 3)
        rows.append(row)
    correct = sum(r["correct"] for r in rows)
    return {"source": source, "correct": correct, "total": len(rows),
            "accuracy": round(100 * correct / len(rows), 1), "rows": rows}


if __name__ == "__main__":
    from ai_sql.db import connect
    report = run_benchmark(connect())
    for r in report["rows"]:
        print(("PASS " if r["correct"] else "FAIL ") + r["question"], r["error"])
    print(f"\n{report['source']}: {report['correct']}/{report['total']} correct ({report['accuracy']}%)")
