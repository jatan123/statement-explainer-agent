"""End-to-end agent eval — calls Claude, needs ANTHROPIC_API_KEY.

Each question passes only if ALL of these hold:
- every required amount appears in the reply
- the reply mentions at least one keyword from each required group
- the agent escalated if and only if it should have
- the number-grounding check passed (no amounts the tools didn't return)
- no forbidden text appears (e.g. another customer's balance, or "verified" for a suspicious charge)

Writes evals/results.md.

    python evals/run_agent_eval.py
"""

import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from explainer import StatementAgent  # noqa: E402
from explainer.agent import amounts_in_text  # noqa: E402


def grade(q: dict, r) -> list[str]:
    problems = []
    said = amounts_in_text(r.text)
    missing = [a for a in q["must_include_amounts"] if a not in said]
    if missing:
        problems.append(f"missing amounts {missing}")
    low = r.text.lower()
    for group in q["must_mention_any"]:
        if not any(k.lower() in low for k in group):
            problems.append(f"didn't mention any of {group}")
    escalated = bool(r.escalations)
    if escalated != q["should_escalate"]:
        problems.append("should have escalated" if q["should_escalate"] else "escalated unnecessarily")
    if not r.numbers_ok:
        problems.append(f"unsupported amounts {r.unsupported_amounts}")
    for bad in q.get("must_not_include", []):
        if bad.lower() in low:
            problems.append(f"contains forbidden '{bad}'")
    return problems


def main() -> None:
    qs = [json.loads(l) for l in (ROOT / "evals/questions.jsonl").read_text().splitlines() if l.strip()]
    rows = []
    for q in qs:
        r = StatementAgent(q["customer"]).ask(q["question"])
        problems = grade(q, r)
        rows.append({**q, "ok": not problems, "problems": problems, "latency_ms": r.latency_ms,
                     "tokens": r.input_tokens + r.output_tokens, "tool_calls": len(r.tool_calls),
                     "retried": r.retried_for_numbers, "numbers_ok": r.numbers_ok, "escalated": bool(r.escalations), "model": r.model})
        print(f"{'PASS' if not problems else 'FAIL'} {q['id']} {'; '.join(problems)}")
        time.sleep(0.5)

    def frac(sel):
        return f"{sum(x['ok'] for x in sel)}/{len(sel)}"

    cats = sorted({r["category"] for r in rows})
    esc = [r for r in rows if r["should_escalate"]]
    no_esc = [r for r in rows if not r["should_escalate"]]
    summary = {
        "model": rows[0]["model"],
        "overall_pass": frac(rows),
        **{f"pass_{c}": frac([r for r in rows if r["category"] == c]) for c in cats},
        "number_grounding_pass": f"{sum(r['numbers_ok'] for r in rows)}/{len(rows)}",
        "replies_needing_number_retry": sum(r["retried"] for r in rows),
        "escalation_recall": f"{sum(r['escalated'] for r in esc)}/{len(esc)}",
        "unnecessary_escalations": sum(r["escalated"] for r in no_esc),
        "median_latency_ms": int(statistics.median(r["latency_ms"] for r in rows)),
        "avg_tool_calls": round(statistics.mean(r["tool_calls"] for r in rows), 1),
        "avg_tokens_per_question": int(statistics.mean(r["tokens"] for r in rows)),
    }
    out = ["# Agent eval results", "", f"Run: {time.strftime('%Y-%m-%d %H:%M')}", ""]
    out += [f"- **{k.replace('_', ' ')}**: {v}" for k, v in summary.items()]
    out += ["", "## Failures", ""]
    out += [f"- `{r['id']}` ({r['customer']}) {r['question']} — {'; '.join(r['problems'])}" for r in rows if not r["ok"]] or ["None"]
    (ROOT / "evals/results.md").write_text("\n".join(out) + "\n")
    print(json.dumps(summary, indent=2))
    print("Wrote evals/results.md")


if __name__ == "__main__":
    main()
