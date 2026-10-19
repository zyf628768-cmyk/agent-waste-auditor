from decimal import Decimal
from .models import money, financial


@financial
def human_costs(task):
    """Human minutes exclude rework minutes. Waiting is never wage-converted."""
    if "hourly_rate" not in task:
        return []
    result = []
    for field, category in (("human_minutes", "human"), ("rework_minutes", "rework")):
        if field in task:
            result.append({"event_id": "task-human-" + field, "task_id": task["task_id"], "category": category,
                           "source": "task_metadata",
                           "origin": "manual", "currency": task["currency"],
                           "amount": str(money(task[field]) * money(task["hourly_rate"]) / 60)})
    return result


@financial
def calculate(task, totals, unknown_count, human_events=False, estimated_used=False):
    required = ("baseline_minutes", "human_minutes", "rework_minutes", "hourly_rate", "currency")
    if not all(k in task for k in required):
        return {"status": "unavailable", "reason": "reliable baseline, hourly rate and complete human effort required"}
    if human_events:
        return {"status": "unavailable", "reason": "human event charges and task human costs may overlap; reconcile first"}
    if unknown_count or any(c != task["currency"] for c in totals):
        return {"status": "unavailable", "reason": "unknown costs or multiple currencies require reconciliation"}
    if task.get("status") != "success" or task.get("accepted") is not True:
        return {"status": "unavailable", "reason": "task not successfully accepted"}
    baseline = money(task["baseline_minutes"]) * money(task["hourly_rate"]) / 60
    actual = sum((money(x) for x in totals.get(task["currency"], {}).values()), Decimal(0))
    saved = baseline - actual
    estimated = estimated_used or money(totals.get(task["currency"], {}).get("estimated", "0")) > 0
    return {"status": "verified_basis" if task.get("baseline_verified") is True and not estimated else "scenario_estimate",
            "currency": task["currency"], "baseline_cost": str(baseline), "total_cost": str(actual),
            "net_savings": str(saved), "roi": str(saved / actual) if actual else None,
            "assumptions": ["user-entered baseline and human effort", "rework minutes exclude other human minutes",
                            "ROI = (baseline - task cost) / task cost; zero cost has undefined ROI"]}
