from collections import defaultdict
from .costs import aggregate
from .models import money
from decimal import Decimal


def compare(reports, by="agent"):
    if by not in {"agent", "model", "prompt_strategy", "workflow"}:
        raise ValueError("invalid comparison dimension")
    groups, excluded = defaultdict(list), []
    seen = set()
    for report in reports:
        for task in report["tasks"]:
            key_id = (task["task_id"], task["agent"])
            if key_id in seen:
                raise ValueError("duplicate task in comparison")
            seen.add(key_id)
            key = (task.get("task_key"), task.get("difficulty"), task.get("acceptance_id"), task["cost_coverage"]["complete"])
            if not all(key[:3]) or task["agent"] == "mixed":
                excluded.append({"task_id": task["task_id"], "reason": "missing comparable task/acceptance/difficulty/agent"})
            elif not task.get(by):
                excluded.append({"task_id": task["task_id"], "reason": "comparison dimension unavailable"})
            else:
                groups[key].append(task)
    out = []
    for (task_key, difficulty, acceptance, coverage), tasks in groups.items():
        agents = []
        for agent in sorted({t[by] for t in tasks}):
            subset = [t for t in tasks if t[by] == agent]
            known_outcomes = sum(t["status"] in {"success", "failed"} and isinstance(t["accepted"], bool) for t in subset)
            successes = sum(t["status"] == "success" and t["accepted"] is True for t in subset)
            totals = []
            for t in subset:
                for cur, bucket in t["totals"].items():
                    totals.extend({"currency": cur, "origin": origin, "amount": value} for origin, value in bucket.items())
            agents.append({"agent": agent, "dimension": by, "attempts": len(subset), "known_outcomes": known_outcomes,
                           "success_rate": str(Decimal(successes) / known_outcomes) if known_outcomes else None,
                           "totals": aggregate(totals), "human_minutes": str(sum(money(t["human_minutes"]) + money(t.get("rework_minutes") or 0) for t in subset)) if all(t["human_minutes"] is not None and t["rework_minutes"] is not None for t in subset) else None,
                           "elapsed_seconds": [t["elapsed_seconds"] for t in subset], "rework_events": sum(t["rework_events"] for t in subset)})
        out.append({"task_key": task_key, "difficulty": difficulty, "acceptance_id": acceptance,
                    "cost_coverage_complete": coverage, "comparable": len(agents) >= 2, "agents": agents})
    return {"schema_version": "1.0", "report_type": "comparison", "synthetic": bool(reports) and all(r.get("synthetic") for r in reports), "dimension": by, "groups": out, "excluded": excluded,
            "caution": "No global ranking; groups separate task identity, difficulty, acceptance and observed cost coverage. Small samples are descriptive."}
