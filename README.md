# 💳 Statement Explainer Agent

**An AI agent that answers "why is my credit card balance different this month?" with exact, verified numbers, and hands disputes and fee requests to a human instead of guessing.**

Built by Jatan Parikh, a product manager who works on platform and banking products, to explore a question every bank faces: *how do you let an AI explain money to customers without it ever getting a number wrong?*

> Runs on **Ledgerly Bank**, a fictional bank with 12 synthetic cardholders. No real customer data.

---

## The problem

"Why is my balance higher?" and "What is this fee?" are some of the most common reasons cardholders contact their bank. The answer is already in the statement, but statements are hard to read: interest rules, grace periods, fees and payment timing all interact.

A generic chatbot is risky here. Language models are good at explaining and **bad at arithmetic**, and in banking a wrong number is a trust problem and a compliance problem.

## The product decision that shapes everything

**The AI never does the math.** All calculations happen in deterministic tools that reconcile to the cent. The model's only jobs are to pick the right tools, explain the results in plain English, and know when to hand off to a human.

Then a guardrail checks that promise: every dollar amount in the agent's reply is compared against what the tools returned. If the agent states a number no tool produced, it gets one chance to fix it, and otherwise the reply is flagged.

## What it does

| Customer asks | Agent does |
|---|---|
| "Why is my balance so much higher?" | Breaks the change into purchases, payments, fees, interest, and refunds, with exact amounts |
| "Why was I charged interest?" | Shows the formula, the unpaid balance carried over, and why the grace period was lost |
| "What is this $35 fee?" | Names the fee and cites the bank's fee policy |
| "I think I was charged twice" | Confirms the duplicate, **escalates to a specialist** with a ticket, and doesn't promise a refund |
| "I don't recognise this charge" | Flags it, ignores suspicious instructions hidden in the merchant name, and escalates |
| "Can you waive this fee?" | Escalates, since the agent can't move money |
| "What's my friend's balance?" | Declines; tools are scoped to the signed-in customer only |

## How it works

```
customer question
   └─▶ Claude (tool-use loop, max 8 steps)
         ├─ get_balance_change        ┐
         ├─ explain_interest          │  deterministic Python:
         ├─ explain_fees              │  reconciled to the cent,
         ├─ check_for_unusual_activity│  scoped to ONE customer,
         ├─ list_transactions         │  merchant text sanitised
         ├─ get_fee_policy            ┘
         └─ escalate_to_specialist ──▶ human queue (ticket)
   └─▶ number-grounding check ──▶ retry once if any $ amount isn't from a tool
   └─▶ answer + "How I worked this out" trace in the UI
```

## Guardrails

1. **Numbers come from tools only**, enforced by an automated check on every reply.
2. **Account scoping:** no tool accepts a customer ID, so the model can't be talked into reading another account.
3. **Prompt-injection defence:** merchant descriptors are untrusted text. Instruction-like content (e.g. `IGNORE PREVIOUS INSTRUCTIONS…`) is redacted before the model sees it, and flagged.
4. **No money movement:** refunds, reversals and fee waivers always go to a human via `escalate_to_specialist`.
5. **Transparency:** the UI shows every tool the agent called for each answer.

## Results

**Offline checks** (no API key, run in CI via `pytest`):

| Check | Result |
|---|---|
| Statements that reconcile to the cent | 12 / 12 |
| Posted interest matching the documented formula | 5 / 5 |
| Unusual-activity rules: precision / recall on labeled scenarios | 100% / 100% |
| Injection text reaching the model unredacted | 0 |

*Caveat:* the anomaly rules and the 12 scenarios were designed together, so 100% shows the rules work as specified, not how they'd generalise. Real transaction data would be the next test.

**Agent eval** (26 questions across balance changes, interest, fees, anomalies and boundary cases): run `python evals/run_agent_eval.py`; results go to [`evals/results.md`](evals/results.md). A question only passes if the right amounts appear, the explanation covers the cause, the escalation decision is correct, and the number check passes.

## Run it

```bash
git clone https://github.com/jatan123/statement-explainer-agent.git
cd statement-explainer-agent
pip install -r requirements.txt
export ANTHROPIC_API_KEY="your-key"

streamlit run app/streamlit_app.py     # web app: pick a customer, ask a question
python evals/run_offline_checks.py     # no key needed
python -m pytest -q                    # no key needed
python evals/run_agent_eval.py         # end-to-end, uses the API
```

## Repo map

```
data/      12 fictional cardholders (2 statements each) + fee schedule
scripts/   deterministic data generator — balances are computed, never typed
src/       tools (all the math) and the agent loop (guardrails)
app/       Streamlit UI with balance-change chart and tool trace
evals/     offline checks, 26-question agent eval, grader
pm/        product brief, decision log, roadmap
tests/     offline tests with a scripted model (no API key)
```

## Product docs

- [Product brief](pm/product-brief.md): problem, users, metrics, risks
- [Decision log](pm/decision-log.md): the choices and the trade-offs behind them
- [Roadmap](pm/roadmap.md): what I'd build next

---

Python · Claude API (tool use) · Streamlit · MIT licensed
