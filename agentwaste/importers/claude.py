"""Experimental assistant-message JSONL adapter; deduplicates usage by message id."""
from ..models import event, fingerprint


def convert(rows):
    out, messages, tools, warnings = [], {}, {}, ["EXPERIMENTAL_CLAUDE_PROFILE", "NATIVE_TASK_OUTCOME_UNAVAILABLE"]
    sessions = {row["sessionId"] for _, row in rows if row.get("sessionId")}
    if len(sessions) > 1:
        raise ValueError("split Claude sessions before import")
    for line, row in rows:
        version = row.get("version")
        if version and not str(version).startswith("2."):
            raise ValueError("unsupported Claude Code major version")
        if not version:
            warnings.append("VERSION_UNAVAILABLE")
        if row.get("type") != "assistant":
            continue
        msg = row.get("message") or {}
        if not msg.get("id") or not row.get("sessionId"):
            raise ValueError("Claude assistant message/session id required")
        base = {"schema_version": "1.0", "task_id": row["sessionId"], "agent": "claude-code",
                "timestamp": row.get("timestamp"), "source_line": line}
        usage = msg.get("usage")
        if usage:
            e = dict(base, id="claude-" + msg["id"], kind="model", model=msg.get("model"))
            # Claude input excludes reads/writes; canonical input includes both.
            if "input_tokens" in usage and all(k in usage for k in ("cache_read_input_tokens", "cache_creation_input_tokens")):
                e["input_tokens"] = usage["input_tokens"] + usage.get("cache_read_input_tokens", 0) + usage.get("cache_creation_input_tokens", 0)
            else:
                warnings.append("TOKEN_USAGE_INCOMPLETE")
            for src, dst in (("output_tokens", "output_tokens"), ("cache_read_input_tokens", "cached_tokens"),
                             ("cache_creation_input_tokens", "cache_write_tokens")):
                if src in usage:
                    e[dst] = usage[src]
            if "cached_tokens" not in e:
                warnings.append("CACHE_USAGE_UNAVAILABLE")
            prior = messages.get(msg["id"])
            if prior and prior.get("model") != e.get("model"):
                raise ValueError("conflicting model for Claude message id")
            messages[msg["id"]] = event(e)
        for block in msg.get("content", []):
            if isinstance(block, dict) and block.get("type") == "tool_use":
                cid = block.get("id")
                if not cid:
                    raise ValueError("Claude tool id missing")
                tools[cid] = event(dict(base, id="claude-tool-" + cid, kind="tool", action=block.get("name", "unknown"),
                                        signature=fingerprint([block.get("name"), block.get("input")]), status="unknown"))
    out.extend(messages.values())
    out.extend(tools.values())
    if not out and rows:
        raise ValueError("unsupported Claude transcript structure")
    return sorted(out, key=lambda e: (e["timestamp"], e["source_line"])), sorted(set(warnings)), "claude-assistant-structural-v1"
