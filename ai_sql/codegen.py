"""Boilerplate generator: turns an approved question + SQL into a Python function and a pytest test.

It fills a fixed template, so the output is always valid Python and works with no API key. The test
pins the number of rows and columns seen when the code was generated, so it works as a regression test.
"""
import re
import textwrap


def function_name(question):
    words = re.findall(r"[a-z0-9]+", question.lower())
    stop = {"what", "is", "the", "are", "a", "an", "of", "by", "show", "me", "which", "who", "how", "in", "on"}
    name = "_".join(w for w in words if w not in stop)[:40].strip("_") or "query"
    if name[0].isdigit():
        name = "q_" + name
    return "get_" + name


def generate_function(question, sql):
    name = function_name(question)
    body = textwrap.indent(sql.strip(), " " * 8)
    return (f'import sqlite3\n\n\n'
            f'def {name}(conn: sqlite3.Connection) -> list[tuple]:\n'
            f'    """{question}"""\n'
            f'    sql = """\n{body}\n    """\n'
            f'    return conn.execute(sql).fetchall()\n')


def generate_test(question, row_count, column_count, module="queries", db_path="data/retail.db"):
    name = function_name(question)
    return (f'import sqlite3\n\nimport pytest\n\nfrom {module} import {name}\n\n\n'
            f'@pytest.fixture\ndef conn():\n'
            f'    connection = sqlite3.connect("{db_path}")\n'
            f'    yield connection\n    connection.close()\n\n\n'
            f'def test_{name}_runs(conn):\n'
            f'    assert isinstance({name}(conn), list)\n\n\n'
            f'def test_{name}_shape(conn):\n'
            f'    rows = {name}(conn)\n'
            f'    assert len(rows) == {row_count}\n'
            f'    if rows:\n'
            f'        assert len(rows[0]) == {column_count}\n')


def generate_code(question, sql, result_df):
    """Returns (function_code, test_code) for the given question, SQL and its result."""
    return (generate_function(question, sql),
            generate_test(question, len(result_df), len(result_df.columns)))
