"""Heuristic suspicions only, with event/line evidence and explicit exemptions."""
from collections import defaultdict
from .models import money, timestamp


def detect(events, rules=None):
    from .rules import Rules
    rules = rules or Rules()
    events = sorted(events, key=lambda e: timestamp(e["timestamp"]))
    findings, groups = [], defaultdict(list)
    segments = defaultdict(int)

    def add(rule, evs, explanation, advice):
        findings.append({"rule": rule, "severity": "review", "conclusion": "suspected_inefficiency",
                         "task_id": evs[0]["task_id"], "explanation": explanation, "recommendation": advice,
                         "evidence": [{"event_id": e["id"], "source_line": e.get("source_line"),
                                       "status": e.get("status", "unknown"), "signature": e.get("signature")} for e in evs]})

    for e in events:
        if e.get("retry_reason") in {"transient", "user_requested", "idempotent_check"} or e.get("progress") is True:
            segments[e["task_id"]] += 1
            continue
        if e.get("signature") and e["kind"] == "tool":
            groups[(e["task_id"], segments[e["task_id"]], e.get("action"), e["signature"])].append(e)
    windows = []
    for (_, _, action, _), evs in groups.items():
        batch = []
        for e in evs:
            if batch and (timestamp(e["timestamp"]) - timestamp(batch[0]["timestamp"])).total_seconds() > rules.window_seconds:
                windows.append((action, batch))
                batch = []
            batch.append(e)
        if batch:
            windows.append((action, batch))
    for action, evs in windows:
        if len(evs) < rules.repetition_threshold:
            continue
        failed = [e for e in evs if e.get("status") in {"failed", "timeout"}]
        if len(failed) >= rules.repetition_threshold:
            add("repeated_failure", failed, "Repeated identical failed calls meet the configured threshold without declared retry justification.", "Check the root error before another attempt.")
        elif action and "read" in action.lower():
            add("repeated_read", evs, "Repeated reads; file changes and intended verification are not known.", "Review file changes; reuse results when valid.")
        elif action and any(word in action.lower() for word in ("edit", "write", "patch")) and all(e.get("progress") is False for e in evs):
            add("unverified_rework", evs, "Repeated edits explicitly report no verifiable progress.", "Add an acceptance check and inspect the failing change.")
        else:
            add("repeated_call", evs, "Identical call fingerprint repeated; intent must be reviewed.", "Check if repetition is required or cacheable.")
    by_task = defaultdict(list)
    for e in events:
        by_task[e["task_id"]].append(e)
        threshold = rules.high_cost_thresholds.get(e.get("currency"))
        if e.get("progress") is False and e.get("amount") is not None and threshold is not None and e.get("retry_reason", "unknown") == "unknown":
            if money(e["amount"]) >= money(threshold):
                add("cost_without_progress", [e], "Charge exceeds the configured original-currency threshold with explicitly absent progress.", "Review whether the cost produced a reusable result before repeating.")
    for evs in by_task.values():
        seq = []
        # A verified progress marker or justified check breaks a loop candidate.
        for e in evs:
            if e.get("progress") is True or e.get("retry_reason") in {"transient", "user_requested", "idempotent_check"}:
                seq.append({})
            elif e["kind"] == "tool":
                seq.append(e)
        length = 2 * rules.repetition_threshold
        start = 0
        for i, current in enumerate(seq):
            if not current.get("signature"):
                start = i + 1
                continue
            if i - start >= 2 and current["signature"] != seq[i - 2].get("signature"):
                start = i - 1
            if i - start + 1 < length:
                continue
            window = seq[i - length + 1:i + 1]
            signatures = [e.get("signature") for e in window]
            if all(signatures) and signatures[0] != signatures[1] and (timestamp(window[-1]["timestamp"]) - timestamp(window[0]["timestamp"])).total_seconds() <= rules.window_seconds:
                if all(e.get("retry_reason", "unknown") == "unknown" and e.get("progress") is not True for e in window):
                    add("alternating_loop", window, "A/B sequence meets the configured repetition threshold without declared progress.", "Stop and inspect the loop termination condition.")
                    break
        failed = None
        for e in evs:
            if e["kind"] == "task":
                if e.get("status") == "failed":
                    failed = e
                elif e.get("status") in {"running", "success"}:
                    failed = None
            elif failed and ((e.get("amount") is not None and money(e["amount"]) > 0) or (e["kind"] == "model" and "amount" not in e)):
                add("cost_after_failure", [failed, e], "A charged step or unpriced model call follows an explicit failed-task marker.", "Confirm whether the task was deliberately reopened.")
        contexts, segment = defaultdict(list), 0
        for e in evs:
            if e.get("progress") is True or e.get("retry_reason") in {"transient", "user_requested", "idempotent_check"}:
                segment += 1
                continue
            if e.get("context_signature") and e.get("input_tokens", 0) >= rules.context_tokens:
                contexts[(segment, e["context_signature"])].append(e)
        for context_events in contexts.values():
            repeated = []
            for e in context_events:
                if repeated and (timestamp(e["timestamp"]) - timestamp(repeated[0]["timestamp"])).total_seconds() > rules.window_seconds:
                    if len(repeated) >= rules.repetition_threshold:
                        add("context_reload", repeated, "Repeated large context fingerprint; caching/intent require review.", "Review context reuse and cache effectiveness.")
                    repeated = []
                repeated.append(e)
            if len(repeated) >= rules.repetition_threshold:
                add("context_reload", repeated, "Repeated large context fingerprint; caching/intent require review.", "Review context reuse and cache effectiveness.")
    return findings
