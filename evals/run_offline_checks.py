"""Offline checks — no API key needed.

1. Every statement reconciles to the cent.
2. Every posted interest charge matches the documented formula.
3. Unusual-activity rules: precision and recall against the labeled scenarios.
4. Instruction-like merchant text never reaches the model unredacted.
5. Every amount the agent eval expects is actually obtainable from the tools
   (so the agent is never graded on a number it had no legal way to state).

    python evals/run_offline_checks.py
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from explainer.agent import amounts_in_results  # noqa: E402
from explainer.tools import StatementTools, load_customers, load_policy  # noqa: E402

ALL_TOOLS = ["get_account_summary", "get_balance_change", "list_transactions", "explain_interest", "explain_fees", "check_for_unusual_activity"]


def run(verbose: bool = True) -> dict:
    customers, policy = load_customers(), load_policy()
    recon = interest_ok = interest_n = 0
    tp = fp = fn = 0
    leaks = []
    details = []

    for cid, c in customers.items():
        t = StatementTools(c, policy)
        recon += t.get_balance_change()["reconciles_to_the_cent"]
        for calc in t.explain_interest()["calculations"]:
            interest_n += 1
            interest_ok += calc["matches_posted"]
        got = {f["type"] for f in t.check_for_unusual_activity()["flags"]}
        want = set(c["labels"]["anomalies"])
        tp += len(got & want); fp += len(got - want); fn += len(want - got)
        if got != want:
            details.append(f"{cid}: flagged {sorted(got)} expected {sorted(want)}")
        blob = json.dumps([t.call(n, {}) for n in ALL_TOOLS] + [t.list_transactions("previous")])
        if "IGNORE PREVIOUS INSTRUCTIONS" in blob.upper():
            leaks.append(cid)

    unobtainable = []
    for line in (ROOT / "evals/questions.jsonl").read_text().splitlines():
        q = json.loads(line)
        t = StatementTools(customers[q["customer"]], policy)
        allowed = amounts_in_results([t.call(n, {}) for n in ALL_TOOLS] + [t.list_transactions("previous")])
        unobtainable += [f"{q['id']}:{a}" for a in q["must_include_amounts"] if a not in allowed]

    res = {
        "statements_reconciling": f"{recon}/{len(customers)}",
        "interest_matches_formula": f"{interest_ok}/{interest_n}",
        "unusual_activity_precision": round(tp / (tp + fp), 3) if tp + fp else None,
        "unusual_activity_recall": round(tp / (tp + fn), 3) if tp + fn else None,
        "injection_text_reaching_model": len(leaks),
        "eval_amounts_not_obtainable_from_tools": unobtainable,
    }
    if verbose:
        print(json.dumps(res, indent=2))
        for d in details:
            print("  mismatch:", d)
    return res


if __name__ == "__main__":
    run()
