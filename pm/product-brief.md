# Product brief: Statement Explainer Agent

## Problem
"Why is my balance higher?", "Why was I charged interest?" and "What is this fee?" drive a large share of card-servicing contacts. The answers are in the statement, but customers can't easily connect payment timing, grace periods, fees and interest. Every one of these contacts costs the bank agent time, and every confusing statement erodes trust.

## Users
1. **Cardholder (primary):** wants a fast, plain-English answer they can trust, with the exact numbers.
2. **Servicing specialist (secondary):** wants only the cases that need human judgement (disputes, fee waivers, suspected fraud), handed over with context.
3. **Risk and compliance (stakeholder):** need assurance that the assistant never misstates amounts, never moves money, and never exposes another customer's data.

## Goals and success metrics
| Goal | Metric | v1 target |
|---|---|---|
| Correct numbers | Replies passing the number-grounding check | 100% |
| Correct explanations | Agent eval pass rate (amounts + cause + escalation) | ≥ 90% |
| Right hand-offs | Escalation recall on cases that need a human | 100% |
| Don't over-escalate | Unnecessary escalations | ≤ 1 per 25 questions |
| Containment | Questions resolved without a human (in production) | Track; aim ≥ 70% |
| Trust | 👍 rate (in production) | ≥ 85% |

**North-star metric (production):** servicing contacts about statement questions per 1,000 active cardholders, going down while satisfaction holds or rises.

## Non-goals (v1)
- Moving money: refunds, reversals, fee waivers, payments.
- Financial advice ("should I pay this off or invest?").
- Disputes end-to-end. The agent starts the hand-off; specialists decide.

## Risks and mitigations
| Risk | Mitigation |
|---|---|
| Wrong number shown to a customer | Tools do all math; automated check blocks any amount not from a tool |
| Prompt injection via merchant names | Descriptors sanitised and flagged before the model sees them |
| Data exposure across customers | Tools are bound to one customer; no tool accepts an ID |
| Over-promising ("we'll refund you") | System prompt forbids promises; refunds and waivers must escalate |
| Model drift after an upgrade | Offline checks run in CI; agent eval re-run on every model change |
| Regulatory explanations (e.g. interest disclosures) | Interest explanations cite the fee schedule; real deployment needs compliance review of the wording |
