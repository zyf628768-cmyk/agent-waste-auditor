from collections import defaultdict
from datetime import timezone
from decimal import Decimal
from .models import VERSION, money, timestamp
from .pricing import PriceBook
from .roi import human_costs, calculate
from .waste import detect


def aggregate(charges):
    totals = {}
    for c in charges:
        bucket = totals.setdefault(c["currency"], {"actual": "0", "estimated": "0", "manual": "0"})
        bucket[c["origin"]] = str(money(bucket[c["origin"]]) + money(c["amount"]))
    return totals


def analyze(data, prices=None):
    book = prices or PriceBook()
    events = sorted(data["events"], key=lambda e: timestamp(e["timestamp"]))
    tasks = {t["task_id"]: t for t in data.get("tasks", [])}
    by_task = defaultdict(list)
    for e in events:
        by_task[e["task_id"]].append(e)
    for tid in tasks:
        by_task.setdefault(tid, [])
    result, all_charges, all_unknowns = [], [], []
    for tid, evs in by_task.items():
        task = tasks.get(tid, {"task_id": tid})
        if task.get("agent") and any(e["agent"] != task["agent"] for e in evs):
            raise ValueError("task agent conflicts with event agent")
        agents = {e["agent"] for e in evs}
        models = {e["model"] for e in evs if e.get("model")}
        charges, unknowns = [], []
        human_events = any(e["kind"] == "human" for e in evs)
        for e in evs:
            charge, reason = None, None
            if "amount" in e:
                charge = {k: e[k] for k in ("amount", "origin", "currency")}
            elif e["kind"] == "model":
                charge, reason = book.estimate(e)
            elif e["kind"] in {"tool", "human"}:
                reason = "COST_UNAVAILABLE"
            if charge:
                charge.update(event_id=e["id"], task_id=tid, category=e.get("category", "model" if e["kind"] == "model" else e["kind"]),
                              failed=e.get("status") in {"failed", "timeout"}, source="event")
                charges.append(charge)
            if reason:
                unknowns.append({"event_id": e["id"], "reason": reason})
        if not human_events:
            charges.extend(human_costs(task))
        else:
            unknowns.append({"event_id": "task-human", "reason": "HUMAN_EFFORT_RECONCILIATION_REQUIRED"})
        if "hourly_rate" not in task and any(money(task.get(k, 0)) > 0 for k in ("human_minutes", "rework_minutes")):
            unknowns.append({"event_id": "task-human", "reason": "HOURLY_RATE_UNAVAILABLE"})
        if not evs:
            unknowns.append({"event_id": "task", "reason": "NO_OBSERVED_EVENTS"})
        totals = aggregate(charges)
        category = {cat: aggregate([c for c in charges if c["category"] == cat]) for cat in sorted({c["category"] for c in charges})}
        times = [timestamp(e["timestamp"]) for e in evs]
        elapsed = str(Decimal(str((max(times) - min(times)).total_seconds()))) if times else None
        # Spans may overlap; elapsed is a timestamp envelope, not sum(duration_ms).
        complete = bool(evs) and not unknowns
        result.append({"task_id": tid, "agent": task.get("agent", next(iter(agents)) if len(agents) == 1 else "mixed"),
                       "task_key": task.get("task_key"), "difficulty": task.get("difficulty"), "acceptance_id": task.get("acceptance_id"),
                       "model": task.get("model", next(iter(models)) if len(models) == 1 else None),
                       "prompt_strategy": task.get("prompt_strategy"), "workflow": task.get("workflow"),
                       "status": task.get("status", "unknown"), "accepted": task.get("accepted"),
                       "synthetic": task.get("synthetic", all(e.get("synthetic") is True for e in evs) if evs else False),
                       "human_minutes": task.get("human_minutes"), "rework_minutes": task.get("rework_minutes"),
                       "totals": totals, "category_totals": category, "failed_step_costs": aggregate([c for c in charges if c.get("failed")]),
                       "unknown_costs": unknowns, "cost_coverage": {"known_events": sum("amount" in e or any(c["event_id"] == e["id"] for c in charges) for e in evs if e["kind"] in {"model", "tool", "human"}),
                       "cost_bearing_events": sum(e["kind"] in {"model", "tool", "human"} for e in evs), "complete": complete},
                       "elapsed_seconds": elapsed, "duration_sum_ms": sum(e.get("duration_ms", 0) for e in evs),
                       "queue_ms": sum(e.get("queue_ms", 0) for e in evs), "human_wait_ms": sum(e.get("human_wait_ms", 0) for e in evs),
                       "rework_events": sum(e.get("category") == "rework" for e in evs),
                       "roi": calculate(task, totals, len(unknowns), human_events)})
        all_charges.extend(charges)
        all_unknowns.extend(unknowns)
    successes = sum(t["status"] == "success" and t["accepted"] is True for t in result)
    totals = aggregate(all_charges)
    dates = sorted({timestamp(e["timestamp"]).astimezone(timezone.utc).date().isoformat() for e in events})
    event_dates = {e["id"]: timestamp(e["timestamp"]).astimezone(timezone.utc).date().isoformat() for e in events}
    trend = [{"date_utc": d, "totals": aggregate([c for c in all_charges if c["source"] == "event" and event_dates.get(c["event_id"]) == d])} for d in dates]
    enriched = {c["event_id"]: c for c in all_charges if c["source"] == "event"}
    waste_events = [dict(e, **{k: enriched[e["id"]][k] for k in ("amount", "currency")}) if e["id"] in enriched else e for e in events]
    return {"schema_version": VERSION, "report_type": "audit", "synthetic": bool(result) and all(t["synthetic"] for t in result),
            "totals": totals, "tasks": result, "charges": all_charges, "findings": detect(waste_events),
            "coverage": {"events": len(events), "tasks": len(result), "unknown_cost_items": len(all_unknowns),
                         "warnings": data.get("warnings", []), "scope": "specified files only; unobserved costs cannot be inferred"},
            "timeline": [{k: e[k] for k in ("id", "task_id", "timestamp", "kind", "status") if k in e} for e in events],
            "trend": trend, "high_cost_steps": [c for cur in sorted({c["currency"] for c in all_charges}) for c in sorted([c for c in all_charges if c["currency"] == cur and c["source"] == "event"], key=lambda c: -money(c["amount"]))[:20]],
            "successful_tasks": successes,
            "average_cost_per_success": {cur: str(sum((money(v) for v in bucket.values()), Decimal(0)) / successes) for cur, bucket in totals.items()} if successes and not all_unknowns else None,
            "average_cost_definition": "all observed task costs including failures / accepted successes; partial scope; currencies kept separate"}
