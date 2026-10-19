"""Completed Responses/Chat Completions objects, one JSON object per line."""
from ..models import event


def convert(rows):
    out, warnings, seen = [], [], set()
    for line, row in rows:
        if row.get("object") not in {"response", "chat.completion"}:
            raise ValueError(f"unsupported OpenAI object at line {line}; streaming/usage aggregates unsupported")
        if not row.get("id") or row["id"] in seen:
            raise ValueError("OpenAI response id missing or duplicated")
        seen.add(row["id"])
        usage = row.get("usage") or {}
        chat = row["object"] == "chat.completion"
        inp, output = ("prompt_tokens", "completion_tokens") if chat else ("input_tokens", "output_tokens")
        from datetime import datetime, timezone
        ts = row.get("created_at", row.get("created"))
        if not isinstance(ts, (int, float)):
            raise ValueError("OpenAI creation timestamp missing")
        e = {"schema_version": "1.0", "id": row["id"], "task_id": row.get("task_id", row["id"]),
             "agent": "openai-api", "timestamp": datetime.fromtimestamp(ts, timezone.utc).isoformat(),
             "kind": "model", "model": row.get("model"), "source_line": line,
             "status": "success" if chat or row.get("status") == "completed" else "unknown"}
        for src, dst in ((inp, "input_tokens"), (output, "output_tokens")):
            if src in usage:
                e[dst] = usage[src]
        details = usage.get("prompt_tokens_details" if chat else "input_tokens_details") or {}
        if "cached_tokens" in details:
            e["cached_tokens"] = details["cached_tokens"]
        else:
            warnings.append("CACHE_USAGE_UNAVAILABLE")
        out.append(event(e))
    return out, sorted(set(warnings)) or ([] if out else ["EMPTY_INPUT"]), "openai-completed-objects-v1"
