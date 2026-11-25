import subprocess
import sys

from ai_sql.codegen import function_name, generate_code
from ai_sql.db import run_query


def test_function_name_is_valid_identifier():
    assert function_name("What is the total revenue?") == "get_total_revenue"
    assert function_name("5 best products").isidentifier()


def test_generated_code_and_test_pass(conn, db_path, tmp_path):
    """The generated function and its generated pytest test actually run and pass."""
    question = "Top 5 customers by spend"
    sql = ("SELECT c.name, SUM(o.total_amount) AS spend FROM customers c "
           "JOIN orders o ON o.customer_id = c.customer_id GROUP BY c.customer_id "
           "ORDER BY spend DESC LIMIT 5")
    code, test = generate_code(question, sql, run_query(conn, sql))
    (tmp_path / "queries.py").write_text(code)
    (tmp_path / "test_queries.py").write_text(test.replace("data/retail.db", str(db_path)))
    result = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
                            cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout
    assert "2 passed" in result.stdout
