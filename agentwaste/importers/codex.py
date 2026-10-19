"""Experimental rollout shape adapter; cumulative usage avoids repeated snapshots."""
import json
from ..models import event, fingerprint


def convert(rows):
    meta = [r.get("payload", {}) for _, r in rows if r.get("type") == "session_meta"]
    if len(meta) != 1 or not meta[0].get("id"):
        raise ValueError("Codex session_meta.id required")
    version = meta[0].get("cli_version", "")
    if version and not str(version).startswith("0."):
        raise ValueError("unsupported Codex major version")
    task = meta[0]["id"]
    model, totals, out, pending = None, {}, [], {}
    gap, changed_model = False, False
    warnings = ["EXPERIMENTAL_CODEX_PROFILE", "NATIVE_TASK_OUTCOME_UNAVAILABLE"]
    if not version:
        warnings.append("VERSION_UNAVAILABLE")
    for line, row in rows:
        p = row.get("payload") or {}
        typ = row.get("type")
        base = {"schema_version": "1.0", "id": f"codex-{line}", "task_id": task, "agent": "codex",
                "timestamp": row.get("timestamp"), "source_line": line}
        if typ == "turn_context":
            changed_model = changed_model or bool(totals and p.get("model") != model)
            model = p.get("model")
        elif typ == "event_msg" and p.get("type") == "token_count":
            current = (p.get("info") or {}).get("total_token_usage")
            if not current:
                warnings.append("CUMULATIVE_USAGE_UNAVAILABLE")
                out.append(event(dict(base, kind="model", model=model, usage_complete=False)))
                gap = True
                continue
            keys = {"input_tokens": "input_tokens", "output_tokens": "output_tokens",
                    "cached_input_tokens": "cached_tokens", "cache_write_input_tokens": "cache_write_tokens"}
            if any(k in current and (isinstance(current[k], bool) or not isinstance(current[k], int) or current[k] < totals.get(k, 0)) for k in keys):
                raise ValueError("invalid or reset Codex cumulative usage; split session")
            if totals == current:
                continue
            e = dict(base, kind="model", model=model)
            if not all(k in current for k in ("input_tokens", "output_tokens", "cached_input_tokens")) or gap:
                e["usage_complete"] = False
                warnings.append("USAGE_GAP")
            for src, dst in keys.items():
                if src in current:
                    e[dst] = current[src] - totals.get(src, 0)
            totals = dict(current)
            gap = not all(k in current for k in ("input_tokens", "output_tokens", "cached_input_tokens"))
            if changed_model:
                # A changed model between cumulative snapshots has no per-model ledger.
                e.pop("model", None)
                e["usage_complete"] = False
                warnings.append("AMBIGUOUS_MODEL_USAGE")
            changed_model = False
            if e.get("usage_complete") is False and e.get("cached_tokens", 0) + e.get("cache_write_tokens", 0) > e.get("input_tokens", 0):
                e.pop("input_tokens", None)
            if not any(e.get(k, 0) for k in keys.values()):
                continue
            if "cached_tokens" not in e:
                warnings.append("CACHE_USAGE_UNAVAILABLE")
            out.append(event(e))
        elif typ == "response_item" and p.get("type") == "function_call":
            cid = p.get("call_id")
            if not cid or cid in pending:
                raise ValueError("invalid Codex call id")
            args = p.get("arguments", "")
            try:
                args = json.loads(args)
            except (ValueError, TypeError):
                pass
            e = event(dict(base, kind="tool", action=p.get("name", "unknown"),
                           signature=fingerprint([p.get("name"), args]), status="unknown"))
            pending[cid] = e
            out.append(e)
        elif typ == "response_item" and p.get("type") == "function_call_output":
            # Output prose cannot reliably prove exit status; never infer success.
            if p.get("call_id") not in pending:
                warnings.append("UNMATCHED_TOOL_OUTPUT")
    if not out:
        warnings.append("NO_SUPPORTED_EVENTS")
    return out, sorted(set(warnings)), "codex-rollout-structural-v1"
