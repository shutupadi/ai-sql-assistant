import pandas as pd

from ai_sql.benchmark import BENCHMARK, evaluate, results_match, run_benchmark
from ai_sql.db import run_query


def test_same_rows_in_different_order_match():
    a = pd.DataFrame({"x": ["A", "B"], "y": [1.001, 2.0]})
    b = pd.DataFrame({"name": ["B", "A"], "total": [2.0, 1.0]})
    assert results_match(a, b)


def test_different_values_do_not_match():
    a = pd.DataFrame({"x": [1, 2]})
    assert not results_match(a, pd.DataFrame({"x": [1, 3]}))
    assert not results_match(a, pd.DataFrame({"x": [1]}))


def test_all_reference_queries_run(conn):
    for _, reference in BENCHMARK:
        run_query(conn, reference)


def test_broken_sql_is_scored_wrong_not_crash(conn):
    row = evaluate(conn, "q", "SELECT nope FROM orders", "SELECT COUNT(*) FROM orders")
    assert row["correct"] is False and "nope" in row["error"]


def test_offline_benchmark(conn):
    report = run_benchmark(conn, mode="offline")
    assert report["total"] == 10
    assert report["correct"] >= 8
    failed = [r["question"] for r in report["rows"] if not r["correct"]]
    assert "Which city has the highest average order value?" in failed   # known limitation
