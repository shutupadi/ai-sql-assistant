"""Streamlit app: ask a business question in English, get SQL, results, code and tests.

Run:  streamlit run app.py
"""
from pathlib import Path

import pandas as pd
import streamlit as st

from ai_sql import feedback
from ai_sql.benchmark import run_benchmark
from ai_sql.codegen import generate_code
from ai_sql.db import DEFAULT_DB, connect, get_schema, run_query
from ai_sql.generator import generate_sql, get_openai_client

st.set_page_config(page_title="AI SQL Assistant", layout="wide")

if not Path(DEFAULT_DB).exists():
    from data.create_db import create_db
    create_db()


@st.cache_resource
def get_conn():
    return connect()


conn = get_conn()
has_key = get_openai_client() is not None

st.title("AI-Assisted SQL Generator")
st.caption(f"Ask a question about the retail database. Generator: "
           f"{'OpenAI API' if has_key else 'offline rules (set OPENAI_API_KEY to use OpenAI)'}")

ask_tab, bench_tab, feedback_tab, schema_tab = st.tabs(["Ask", "Benchmark", "Feedback", "Schema"])

# ---------- Ask: question -> SQL -> results -> feedback -> code ----------
with ask_tab:
    examples = ["Show monthly revenue", "Top 5 customers in Delhi", "Revenue by category",
                "Which products are low on stock?", "How many orders were cancelled?"]
    question = st.text_input("Business question", placeholder=" / ".join(examples[:3]))
    st.caption("Try: " + " · ".join(examples))

    if st.button("Generate SQL", type="primary") and question:
        result = generate_sql(conn, question)
        st.session_state.update(question=question, sql=result["sql"], source=result["source"])

    if st.session_state.get("question"):
        if not st.session_state.get("sql"):
            st.warning("Sorry, I couldn't turn that into SQL. Try rephrasing it.")
        else:
            st.write(f"Source: **{st.session_state['source']}**")
            sql = st.text_area("SQL (you can edit it before running)", st.session_state["sql"], height=180)
            try:
                df = run_query(conn, sql)
                st.dataframe(df, width="stretch")
                if df.shape[1] == 2 and len(df) > 1 and pd.api.types.is_numeric_dtype(df.iloc[:, 1]):
                    st.bar_chart(df.set_index(df.columns[0]))
            except Exception as exc:
                df = None
                st.error(f"Query failed: {exc}")

            st.write("Was this answer correct?")
            up, down, _ = st.columns([1, 1, 6])
            if up.button("👍 Correct"):
                feedback.save_feedback(conn, st.session_state["question"], sql, 1,
                                       source=st.session_state["source"])
                st.success("Saved. This SQL will be reused for the same question.")
            if down.button("👎 Wrong"):
                feedback.save_feedback(conn, st.session_state["question"], sql, -1,
                                       source=st.session_state["source"])
                st.info("Saved. Edit the SQL above and give it a 👍 to teach the correct answer.")

            if df is not None:
                with st.expander("Generate Python function + pytest test"):
                    code, test = generate_code(st.session_state["question"], sql, df)
                    st.code(code, language="python")
                    st.code(test, language="python")

# ---------- Benchmark: generated vs hand-written ----------
with bench_tab:
    st.write("Runs 10 business questions through the generator and compares each result set "
             "with a hand-written query.")
    if st.button("Run benchmark"):
        report = run_benchmark(conn)
        st.metric(f"Accuracy ({report['source']})", f"{report['accuracy']}%",
                  f"{report['correct']} of {report['total']} correct", delta_color="off")
        table = pd.DataFrame(report["rows"])[["question", "correct", "seconds", "error", "generated_sql"]]
        st.dataframe(table, width="stretch")

# ---------- Feedback history ----------
with feedback_tab:
    stats = pd.DataFrame(feedback.feedback_stats(conn), columns=["source", "thumbs_up", "thumbs_down"])
    st.dataframe(stats, width="stretch")
    history = pd.read_sql_query("SELECT created_at, rating, source, question, sql FROM query_feedback "
                                "ORDER BY feedback_id DESC", conn)
    st.dataframe(history, width="stretch")

with schema_tab:
    st.code(get_schema(conn), language="sql")
