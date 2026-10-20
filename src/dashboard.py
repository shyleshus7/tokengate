"""Phase 5: Streamlit dashboard that reads the latest results/run_*.json.

Run from the repo root:  streamlit run src/dashboard.py
"""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"


def latest_results_file():
    files = sorted(RESULTS_DIR.glob("run_*.json"))
    return files[-1] if files else None


st.set_page_config(page_title="TokenGate", layout="wide")
st.title("TokenGate - LLM token savings")

path = latest_results_file()
if path is None:
    st.error("No results found. Run `python -m src.benchmark` first.")
    st.stop()

report = json.loads(path.read_text())
totals = report["totals"]
tasks = report["tasks"]
st.caption(f"Results: {path.name} | model: {report['model']} | headroom mode: {report['headroom_mode']}")

# --- Headline numbers -------------------------------------------------------
st.metric("Benchmark $ saved", f"${totals['cost_saved']:.4f}")
col1, col2, col3 = st.columns(3)
col1.metric("Tokens without compression", f"{totals['tokens_before']:,.0f}")
col2.metric("Tokens with compression", f"{totals['tokens_after']:,.0f}")
col3.metric("Compression", f"{totals['compression_pct']}%")

# --- Tokens per task --------------------------------------------------------
st.subheader("Tokens per task")
token_table = pd.DataFrame(
    {
        "Without compression": [t["tokens_before"] for t in tasks.values()],
        "With compression": [t["tokens_after"] for t in tasks.values()],
    },
    index=list(tasks.keys()),
)
st.bar_chart(token_table)

# --- Cost comparison --------------------------------------------------------
st.subheader("Cost comparison")
cost_table = pd.DataFrame(
    {
        "Task": list(tasks.keys()),
        "Tokens before": [t["tokens_before"] for t in tasks.values()],
        "Tokens after": [t["tokens_after"] for t in tasks.values()],
        "Compression %": [t["compression_pct"] for t in tasks.values()],
        "Cost before ($)": [t["cost_before"] for t in tasks.values()],
        "Cost after ($)": [t["cost_after"] for t in tasks.values()],
    }
)
st.dataframe(cost_table, hide_index=True, width="stretch")
c1, c2 = st.columns(2)
c1.metric("Total cost without compression", f"${totals['cost_before']:.4f}")
c2.metric("Total cost with compression", f"${totals['cost_after']:.4f}")

# --- Live monthly extrapolation ---------------------------------------------
st.subheader("Monthly org savings")
ex = report["extrapolation"]
devs = st.slider("Developers", 1, 1000, int(ex["devs"]))
per_day = st.slider("Requests per developer per day", 1, 200, int(ex["requests_per_day"]))
days = int(ex["working_days_per_month"])
monthly = ex["savings_per_request"] * devs * per_day * days
st.metric("Estimated savings per month", f"${monthly:,.2f}")
st.caption(f"{ex['savings_per_request']:.5f} $/request x {devs} devs x {per_day} requests/day x {days} days")

# --- Answers side by side ---------------------------------------------------
st.subheader("Answers: without vs. with compression")
for task_id, t in tasks.items():
    with st.expander(f"{task_id} - {t['question']}"):
        left, right = st.columns(2)
        left.markdown("**Without compression**")
        left.write(t["answer_before"])
        right.markdown("**With compression**")
        right.write(t["answer_after"])
