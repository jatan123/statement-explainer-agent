import sys
from pathlib import Path
from types import SimpleNamespace as NS

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "evals"))

from explainer import StatementAgent, StatementTools, check_numbers, load_customers, load_policy  # noqa: E402
from run_offline_checks import run as offline_checks  # noqa: E402


def text(t):
    return NS(type="text", text=t)


def tool(name, args=None, id="t1"):
    return NS(type="tool_use", name=name, input=args or {}, id=id)


class ScriptedClient:
    """Plays back a fixed sequence of model turns so the agent loop can be tested offline."""

    def __init__(self, turns):
        self.turns, self.calls = list(turns), []
        self.messages = self

    def create(self, **kw):
        self.calls.append(kw)
        return NS(content=self.turns.pop(0), usage=NS(input_tokens=100, output_tokens=20))


def test_offline_checks_all_pass():
    r = offline_checks(verbose=False)
    assert r["statements_reconciling"] == "12/12"
    assert r["interest_matches_formula"] == "5/5"
    assert r["unusual_activity_precision"] == 1.0 and r["unusual_activity_recall"] == 1.0
    assert r["injection_text_reaching_model"] == 0
    assert r["eval_amounts_not_obtainable_from_tools"] == []


def test_agent_runs_tool_then_answers():
    client = ScriptedClient([[tool("get_balance_change")],
                             [text("Your balance rose $1,031.30, mostly from new purchases.")]])
    r = StatementAgent("C01", client=client).ask("Why is my balance higher?")
    assert r.tool_calls[0]["tool"] == "get_balance_change"
    assert r.numbers_ok and not r.retried_for_numbers
    assert client.calls[0]["tools"] and "NEVER do arithmetic" in client.calls[0]["system"]


def test_number_guard_catches_invented_amount_and_retries():
    client = ScriptedClient([[tool("get_balance_change")],
                             [text("You owe an extra $999.99.")],          # invented
                             [text("Your balance rose $1,031.30.")]])      # fixed after feedback
    r = StatementAgent("C01", client=client).ask("Why is my balance higher?")
    assert r.retried_for_numbers and r.numbers_ok
    sent = [m["content"] for m in client.calls[-1]["messages"] if isinstance(m["content"], str)]
    assert any("Automated check" in s and "$999.99" in s for s in sent)


def test_number_guard_flags_if_still_wrong():
    client = ScriptedClient([[tool("get_balance_change")], [text("$999.99")], [text("still $999.99")]])
    r = StatementAgent("C01", client=client).ask("?")
    assert not r.numbers_ok and r.unsupported_amounts == ["999.99"]


def test_escalation_is_recorded():
    client = ScriptedClient([[tool("check_for_unusual_activity")],
                             [tool("escalate_to_specialist", {"reason": "duplicate gym charge", "category": "dispute_duplicate"}, id="t2")],
                             [text("I've sent this to a specialist.")]])
    r = StatementAgent("C05", client=client).ask("Was I charged twice?")
    assert r.escalations and r.escalations[0]["ticket"].startswith("LB-")


def test_tools_cannot_reach_other_customers():
    t = StatementTools(load_customers()["C01"], load_policy())
    assert "error" in t.call("get_balance_change", {"customer_id": "C02"})
    assert "error" in t.call("delete_account", {})


def test_check_numbers_formats():
    assert check_numbers("It was $1,031.30 and $35", [{"a": 1031.3, "b": 35}]) == []
    assert check_numbers("It was $12.00", [{"a": 1.0}]) == ["12.00"]
