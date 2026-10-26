"""Web UI: streamlit run app/streamlit_app.py"""

import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from explainer import StatementAgent, StatementTools, load_customers, load_policy  # noqa: E402

st.set_page_config(page_title="Statement Explainer", page_icon="💳", layout="centered")

try:
    if "ANTHROPIC_API_KEY" in st.secrets:
        os.environ["ANTHROPIC_API_KEY"] = st.secrets["ANTHROPIC_API_KEY"]
except Exception:
    pass

customers = load_customers()
policy = load_policy()

with st.sidebar:
    st.header("Demo customers")
    st.caption("Fictional Ledgerly Bank cardholders, each with a different reason their balance changed.")
    labels = {cid: f"{c['name']} — {c['persona']}" for cid, c in customers.items()}
    cid = st.radio("Signed in as", list(customers), format_func=labels.get, label_visibility="collapsed")
    st.divider()
    st.caption("The assistant can explain and escalate, but it can't move money. Every number comes from the bank's systems, not the AI.")

if st.session_state.get("cid") != cid:
    st.session_state.cid = cid
    st.session_state.messages = []

c = customers[cid]
tools = StatementTools(c, policy)
bc = tools.get_balance_change()

st.title("💳 Statement Explainer")
st.caption(f"{c['name']} · {c['card']} · Statement for {c['cycles'][1]['period_start']} to {c['cycles'][1]['period_end']}")

m1, m2, m3 = st.columns(3)
m1.metric("Last statement", f"${bc['previous_statement_balance']:,.2f}")
m2.metric("This statement", f"${bc['current_statement_balance']:,.2f}", f"{bc['change']:+,.2f}", delta_color="inverse")
m3.metric("Minimum due", f"${c['cycles'][1]['minimum_due']:,.2f}")

totals = {k.replace("_", " "): v for k, v in bc["this_cycle_totals_by_category"].items() if v}
with st.expander("What moved my balance this month", expanded=False):
    st.bar_chart(pd.DataFrame({"amount": totals}), horizontal=True)
    st.caption("Positive amounts add to what you owe; negative amounts reduce it.")

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        if m.get("escalations"):
            for e in m["escalations"]:
                st.info(f"Sent to a specialist · ticket **{e['ticket']}** · {e['category'].replace('_', ' ')}")
        if m.get("numbers_ok") is False:
            st.warning("Some amounts in this answer couldn't be verified against your statement. Please check them.")
        if m.get("trace"):
            with st.expander("How I worked this out"):
                for step in m["trace"]:
                    args = ", ".join(f"{k}={v}" for k, v in step["input"].items())
                    st.markdown(f"- `{step['tool']}({args})`")

if not st.session_state.messages:
    if st.button(f"Try: “{c['question_hint']}”"):
        st.session_state.pending = c["question_hint"]

question = st.chat_input("Ask about your statement…") or st.session_state.pop("pending", None)
if question:
    history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
    st.session_state.messages.append({"role": "user", "content": question})
    try:
        with st.spinner("Checking your statement…"):
            r = StatementAgent(cid).ask(question, history=history)
        st.session_state.messages.append({"role": "assistant", "content": r.text, "trace": r.tool_calls,
                                          "escalations": r.escalations, "numbers_ok": r.numbers_ok})
    except RuntimeError as e:
        st.session_state.messages.append({"role": "assistant", "content": f"⚠️ {e}"})
    st.rerun()
