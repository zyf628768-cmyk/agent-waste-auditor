from collections import defaultdict
from .costs import aggregate
from .models import money, financial
from decimal import Decimal


@financial
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
            coverage = task["cost_coverage"]
            scope = (coverage["complete"], coverage.get("human_effort_known", False),
                     tuple(coverage.get("monetary_basis", [])), tuple(coverage.get("unknown_reasons", [])),
                     tuple(sorted(task["totals"])))
            key = (task.get("task_key"), task.get("difficulty"), task.get("acceptance_id"), scope)
            if not all(key[:3]) or task["agent"] == "mixed":
                excluded.append({"task_id": task["task_id"], "reason": "missing comparable task/acceptance/difficulty/agent"})
            elif not task.get(by):
                excluded.append({"task_id": task["task_id"], "reason": "comparison dimension unavailable"})
            else:
                groups[key].append(task)
    out = []
    for (task_key, difficulty, acceptance, coverage), tasks in sorted(groups.items()):
        agents = []
        for agent in sorted({t[by] for t in tasks}):
            subset = [t for t in tasks if t[by] == agent]
            known_outcomes = sum(t["status"] == "failed" or (t["status"] == "success" and isinstance(t["accepted"], bool)) for t in subset)
            successes = sum(t["status"] == "success" and t["accepted"] is True for t in subset)
            totals = []
            for t in subset:
                for cur, bucket in t["totals"].items():
                    totals.extend({"currency": cur, "origin": origin, "amount": value} for origin, value in bucket.items())
            subtotal = aggregate(totals)
            def divided(count):
                return {cur: {origin: str(money(value) / count) for origin, value in bucket.items()} for cur, bucket in subtotal.items()} if count else None
            durations = sorted(money(t["elapsed_seconds"]) for t in subset if t["elapsed_seconds"] is not None)
            median = (durations[(len(durations) - 1) // 2] + durations[len(durations) // 2]) / 2 if durations else None
            agents.append({"agent": agent, "dimension": by, "attempts": len(subset), "known_outcomes": known_outcomes,
                           "successes": successes, "unknown_outcomes": len(subset) - known_outcomes,
                           "success_rate": str(Decimal(successes) / known_outcomes) if known_outcomes else None,
                           "totals": subtotal, "cost_per_attempt": divided(len(subset)),
                           "cost_per_success": divided(successes) if coverage[0] else None,
                           "human_minutes": str(sum((money(t["human_minutes"]) + money(t["rework_minutes"]) for t in subset), Decimal(0))) if all(t["human_minutes"] is not None and t["rework_minutes"] is not None for t in subset) else None,
                           "elapsed_median_seconds": str(median) if median is not None else None,
                           "elapsed_seconds": [t["elapsed_seconds"] for t in subset], "rework_events": sum(t["rework_events"] for t in subset)})
        out.append({"task_key": task_key, "difficulty": difficulty, "acceptance_id": acceptance,
                    "cost_coverage_complete": coverage[0], "coverage_signature": {"human_effort_known": coverage[1], "monetary_basis": list(coverage[2]), "unknown_reasons": list(coverage[3]), "currencies": list(coverage[4])},
                    "comparable": len(agents) >= 2, "agents": agents})
    return {"schema_version": "1.0", "report_type": "comparison", "synthetic": bool(reports) and all(r.get("synthetic") for r in reports), "dimension": by, "groups": out, "excluded": excluded,
            "caution": "No global ranking; groups separate identity, difficulty, acceptance, cost completeness, monetary basis, human effort coverage, unknown reasons and currencies. Per-attempt/per-success costs avoid misleading unequal totals. Small samples are descriptive."}
