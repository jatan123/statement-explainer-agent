# Decision log

## 1. The model explains; it never calculates
**Options:** (a) give the model the raw transactions and let it work things out; (b) do the math in tools and let the model explain.
**Decision:** (b).
**Why:** LLMs are fluent but unreliable at multi-step arithmetic, and in banking one wrong number is a trust and compliance failure. Deterministic tools give exact, testable answers, and the model's strength (plain-English explanation) is used where it's safest.
**Trade-off:** every new question type needs a tool. That's acceptable: the set of statement questions is finite, and each tool is unit-tested.

## 2. Verify the promise: automated number-grounding check
A rule in the prompt ("never compute numbers") is a hope, not a control. So every dollar amount in a reply is checked against tool outputs. On a mismatch the agent gets one retry with feedback; if it still fails, the reply is flagged in the UI.
**Trade-off:** the agent can't state helpful derived totals the tools don't provide. The fix is to add those totals to the tools, not to relax the check.

## 3. Scope tools to one customer at session start
No tool takes a customer ID. The session binds the tools to the signed-in cardholder, so "show me Daniel's balance" is impossible by construction, not just by instruction.

## 4. Treat merchant text as hostile input
Merchant descriptors come from outside the bank. One test customer has a charge whose descriptor contains "IGNORE PREVIOUS INSTRUCTIONS…". Tools redact instruction-like text and raise a `suspicious_descriptor` flag. The defence is in code, with the prompt as a second layer.

## 5. Escalate rather than act
The agent can explain anything but change nothing. Disputes, unrecognised charges, refund and fee-waiver requests always create a specialist ticket. This keeps the agent useful from day one without needing approvals for money movement, which is the slowest thing to get through risk review.

## 6. Informational vs. actionable flags
A large first-time merchant charge is common (a new sofa, a flight), so `large_new_merchant` is informational; the agent mentions it only if relevant. A duplicate charge or suspicious descriptor is actionable and leads to escalation. Flagging everything would train customers to ignore flags.

## 7. Synthetic data, generated not typed
All 12 customers come from a script that computes balances from transactions, so every statement reconciles by construction and the dataset can be regenerated or extended. Each customer represents one real-world reason a balance changes.

## 8. Simplified interest formula, stated openly
Real cards use average daily balance. The demo uses "unpaid balance × APR ÷ 12" and says so in the fee schedule. The product principle being tested is the architecture (tools do math, the model explains), not interest accounting.
