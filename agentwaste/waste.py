"""Heuristic suspicions only, with event/line evidence and explicit exemptions."""
from collections import defaultdict


def detect(events):
    findings, groups = [], defaultdict(list)

    def add(rule, evs, explanation, advice):
        findings.append({"rule": rule, "severity": "review", "conclusion": "suspected_inefficiency",
                         "task_id": evs[0]["task_id"], "explanation": explanation, "recommendation": advice,
                         "evidence": [{"event_id": e["id"], "source_line": e.get("source_line"),
                                       "status": e.get("status", "unknown"), "signature": e.get("signature")} for e in evs]})

    for e in events:
        if e.get("retry_reason") in {"transient", "user_requested", "idempotent_check"} or e.get("progress") is True:
            continue
        if e.get("signature") and e["kind"] == "tool":
            groups[(e["task_id"], e.get("action"), e["signature"])].append(e)
    for (_, action, _), evs in groups.items():
        if len(evs) < 3:
            continue
        failed = [e for e in evs if e.get("status") in {"failed", "timeout"}]
        if len(failed) >= 3:
            add("repeated_failure", failed, "At least three identical failed calls without declared retry justification.", "Check the root error before another attempt.")
        elif action and "read" in action.lower():
            add("repeated_read", evs, "Repeated reads; file changes and intended verification are not known.", "Review file changes; reuse results when valid.")
        elif action and any(word in action.lower() for word in ("edit", "write", "patch")) and all(e.get("progress") is False for e in evs):
            add("unverified_rework", evs, "Repeated edits explicitly report no verifiable progress.", "Add an acceptance check and inspect the failing change.")
        else:
            add("repeated_call", evs, "Identical call fingerprint repeated; intent must be reviewed.", "Check if repetition is required or cacheable.")
    by_task = defaultdict(list)
    for e in events:
        by_task[e["task_id"]].append(e)
        if e.get("progress") is False and e.get("amount") is not None:
            from .models import money
            if money(e["amount"]) >= 1:
                add("cost_without_progress", [e], "Reported charge >= 1 original currency unit with explicitly absent progress; threshold is heuristic.", "Review whether the cost produced a reusable result before repeating.")
    for evs in by_task.values():
        seq = [e for e in evs if e["kind"] == "tool"]
        for i in range(len(seq) - 5):
            window = seq[i:i + 6]
            signatures = [e.get("signature") for e in window]
            if all(signatures) and signatures[:2] == signatures[2:4] == signatures[4:6] and signatures[0] != signatures[1]:
                if all(e.get("retry_reason", "unknown") == "unknown" and e.get("progress") is not True for e in window):
                    add("alternating_loop", window, "A/B sequence repeated three times without declared progress.", "Stop and inspect the loop termination condition.")
                    break
        failed = None
        for e in evs:
            if e["kind"] == "task":
                failed = e if e.get("status") == "failed" else None
            elif failed and (e.get("amount") is not None or e["kind"] == "model"):
                add("cost_after_failure", [failed, e], "Cost-bearing event after an explicit failed-task marker.", "Confirm whether the task was deliberately reopened.")
        contexts = defaultdict(list)
        for e in evs:
            if e.get("context_signature") and e.get("input_tokens", 0) >= 10_000:
                contexts[e["context_signature"]].append(e)
        for repeated in contexts.values():
            if len(repeated) >= 3:
                add("context_reload", repeated, "Repeated large context fingerprint; caching/intent require review.", "Review context reuse and cache effectiveness.")
    return findings
