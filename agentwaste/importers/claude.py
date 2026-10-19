"""Experimental assistant-message JSONL adapter; deduplicates usage by message id."""
from ..models import event, fingerprint, timestamp


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
        if usage or msg["id"] not in messages:
            usage = usage or {}
            e = dict(base, id="claude-" + msg["id"], kind="model", model=msg.get("model"))
            for key in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"):
                if key in usage and (isinstance(usage[key], bool) or not isinstance(usage[key], int) or usage[key] < 0):
                    raise ValueError("invalid Claude usage count")
            # Claude input excludes reads/writes; canonical input includes both.
            if "input_tokens" in usage and all(k in usage for k in ("cache_read_input_tokens", "cache_creation_input_tokens")):
                e["input_tokens"] = usage["input_tokens"] + usage.get("cache_read_input_tokens", 0) + usage.get("cache_creation_input_tokens", 0)
            else:
                warnings.append("TOKEN_USAGE_INCOMPLETE")
                e["usage_complete"] = False
            for src, dst in (("output_tokens", "output_tokens"), ("cache_read_input_tokens", "cached_tokens"),
                             ("cache_creation_input_tokens", "cache_write_tokens")):
                if src in usage:
                    e[dst] = usage[src]
            if "cached_tokens" not in e:
                warnings.append("CACHE_USAGE_UNAVAILABLE")
            prior = messages.get(msg["id"])
            if prior and prior.get("model") != e.get("model"):
                raise ValueError("conflicting model for Claude message id")
            if prior:
                for field in ("input_tokens", "cached_tokens", "cache_write_tokens"):
                    if field in prior and field in e and prior[field] != e[field]:
                        raise ValueError("conflicting input usage for Claude message id")
                if e.get("output_tokens", 0) < prior.get("output_tokens", 0):
                    raise ValueError("regressing Claude output snapshot")
                # Preserve the call's start time rather than the final duplicate block.
                e["timestamp"] = prior["timestamp"]
            messages[msg["id"]] = event(e)
        for block in msg.get("content", []):
            if isinstance(block, dict) and block.get("type") == "tool_use":
                cid = block.get("id")
                if not cid:
                    raise ValueError("Claude tool id missing")
                candidate = event(dict(base, id="claude-tool-" + cid, kind="tool", action=block.get("name", "unknown"),
                                        signature=fingerprint([block.get("name"), block.get("input")]), status="unknown"))
                if cid in tools and tools[cid]["signature"] != candidate["signature"]:
                    raise ValueError("conflicting Claude tool id")
                tools.setdefault(cid, candidate)
    out.extend(messages.values())
    out.extend(tools.values())
    if not out and rows:
        raise ValueError("unsupported Claude transcript structure")
    if not rows:
        warnings.append("EMPTY_INPUT")
    return sorted(out, key=lambda e: (timestamp(e["timestamp"]), e["source_line"])), sorted(set(warnings)), "claude-assistant-structural-v1"
