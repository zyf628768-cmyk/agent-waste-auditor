"""Generate declared SYNTHETIC fixtures, never sample user logs."""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def save(name, data):
    (ROOT / "examples" / name).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def main():
    (ROOT / "examples").mkdir(exist_ok=True)
    price = {"id": "SYNTHETIC-2026-v1", "model": "SYNTHETIC-model", "currency": "USD", "source": "SYNTHETIC TEST PRICES; NOT A PROVIDER QUOTE", "effective_from": "2026-01-01", "effective_to": "2026-12-31", "input_per_million": "2", "output_per_million": "8", "cache_read_per_million": "0.5", "cache_write_per_million": "3"}
    save("pricing.json", {"schema_version": "1.0", "prices": [price]})

    def event(id, task, agent="codex", second=0, **kw):
        e = dict(schema_version="1.0", id=id, task_id=task, agent=agent, timestamp=f"2026-10-01T09:{second // 60:02}:{second % 60:02}Z", kind="tool", status="success", synthetic=True)
        e.update(kw)
        return e

    def task(tid, agent="codex", **kw):
        t = dict(task_id=tid, agent=agent, task_key="SYNTHETIC-fix-parser", difficulty="easy", acceptance_id="SYNTHETIC-parser-tests-v1", status="success", accepted=True, baseline_minutes="60", baseline_verified=False, human_minutes="10", rework_minutes="0", hourly_rate="36", currency="USD", synthetic=True)
        t.update(kw)
        return t

    success = [event("SYNTHETIC-s-model", "SYNTHETIC-success", kind="model", model="SYNTHETIC-model", input_tokens=100000, cached_tokens=40000, output_tokens=20000, duration_ms=5000),
               event("SYNTHETIC-s-tool", "SYNTHETIC-success", second=6, action="search", signature="SYNTHETIC-query", amount="0.02", currency="USD", origin="actual"),
               event("SYNTHETIC-s-end", "SYNTHETIC-success", second=12, kind="task")]
    claude = [event("SYNTHETIC-c-model", "SYNTHETIC-claude", agent="claude-code", kind="model", model="SYNTHETIC-model", input_tokens=200000, cached_tokens=20000, output_tokens=30000),
              event("SYNTHETIC-c-tool", "SYNTHETIC-claude", agent="claude-code", second=10, action="search", amount="0.04", currency="USD", origin="actual"),
              event("SYNTHETIC-c-end", "SYNTHETIC-claude", agent="claude-code", second=22, kind="task")]
    waste = []
    for i in range(3):
        waste.append(event(f"SYNTHETIC-fail-{i}", "SYNTHETIC-waste", second=i, action="shell", arguments={"command": "SYNTHETIC failing test"}, status="failed", amount="0.05", currency="USD", origin="actual"))
    for i in range(6):
        waste.append(event(f"SYNTHETIC-loop-{i}", "SYNTHETIC-waste", second=i + 5, action="inspect", signature=f"SYNTHETIC-loop-{i % 2}", amount="0.02", currency="USD", origin="actual"))
    for action, start, amount in (("edit_file", 12, "0.04"), ("read_file", 16, "0.01")):
        for i in range(3):
            waste.append(event(f"SYNTHETIC-{action}-{i}", "SYNTHETIC-waste", second=start + i, action=action, signature="SYNTHETIC same file " + action, progress=False, amount=amount, currency="USD", origin="actual", category="rework" if action == "edit_file" else "tool"))
    for i in range(3):
        waste.append(event(f"SYNTHETIC-context-{i}", "SYNTHETIC-waste", second=20 + i, kind="model", model="SYNTHETIC-model", input_tokens=20000, cached_tokens=0, output_tokens=100, context_signature="SYNTHETIC-large-context"))
    waste.extend([event("SYNTHETIC-no-result", "SYNTHETIC-waste", second=24, action="search", progress=False, amount="2", currency="USD", origin="actual"),
                  event("SYNTHETIC-quality", "SYNTHETIC-waste", second=25, amount="0.50", currency="USD", origin="manual", category="quality"),
                  event("SYNTHETIC-wait", "SYNTHETIC-waste", second=26, kind="wait", duration_ms=60000, queue_ms=10000, human_wait_ms=20000),
                  event("SYNTHETIC-failed-task", "SYNTHETIC-waste", second=30, kind="task", status="failed"),
                  event("SYNTHETIC-after-failure", "SYNTHETIC-waste", second=35, kind="model", model="SYNTHETIC-model", input_tokens=1000, cached_tokens=400, output_tokens=200)])
    for name, events, tasks in (("success", success, [task("SYNTHETIC-success")]), ("waste", waste, [task("SYNTHETIC-waste", status="failed", accepted=False, human_minutes="15", rework_minutes="30")]), ("claude", claude, [task("SYNTHETIC-claude", "claude-code", human_minutes="20")])):
        (ROOT / "examples" / f"{name}.jsonl").write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")
        save(f"{name}.tasks.json", tasks)
    with (ROOT / "examples" / "success.csv").open("w", newline="", encoding="utf-8") as f:
        fields = sorted({k for e in success for k in e})
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for e in success:
            w.writerow({k: str(v).lower() if isinstance(v, bool) else v for k, v in e.items()})
    ts = "2026-10-01T00:00:00Z"
    codex = [{"type": "session_meta", "payload": {"id": "SYNTHETIC-native-codex", "cli_version": "0.142.0"}}, {"type": "turn_context", "payload": {"model": "SYNTHETIC-model"}}, {"type": "event_msg", "timestamp": ts, "payload": {"type": "token_count", "info": {"total_token_usage": {"input_tokens": 1000, "cached_input_tokens": 400, "output_tokens": 200}}}}]
    cl = [{"type": "assistant", "version": "2.0.0", "sessionId": "SYNTHETIC-native-claude", "timestamp": ts, "message": {"id": "SYNTHETIC-msg", "model": "SYNTHETIC-model", "usage": {"input_tokens": 600, "cache_read_input_tokens": 400, "cache_creation_input_tokens": 0, "output_tokens": 200}, "content": [{"type": "text", "text": "SYNTHETIC content discarded"}]}}]
    oa = [{"object": "response", "id": "SYNTHETIC-native-openai", "created_at": 1790812800, "status": "completed", "model": "SYNTHETIC-model", "usage": {"input_tokens": 1000, "output_tokens": 200, "input_tokens_details": {"cached_tokens": 400}}}]
    for name, rows in (("codex-native", codex), ("claude-native", cl), ("openai-native", oa)):
        (ROOT / "examples" / f"{name}.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    print("SYNTHETIC fixtures generated")


if __name__ == "__main__":
    main()
