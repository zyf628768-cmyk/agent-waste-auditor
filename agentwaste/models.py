"""Canonical v1 records. Raw prompts, commands and paths are never persisted."""
import hashlib
import json
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

VERSION = "1.0"


def money(value):
    if isinstance(value, bool):
        raise ValueError("invalid decimal")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError("invalid decimal") from None
    if not result.is_finite() or result < 0:
        raise ValueError("decimal must be finite and nonnegative")
    return result


def redact(value):
    """Defense in depth; arbitrary text is additionally excluded by field allowlists."""
    text = str(value)
    text = re.sub(r"(?i)(?:sk-[\w-]+|bearer\s+\S+|[\w.+-]+@[\w.-]+\.[a-z]{2,})", "[REDACTED]", text)
    text = re.sub(r"(?i)(api[_-]?key|password|cookie|secret|token)\s*[:=]\s*[^\s,;]+", r"\1=[REDACTED]", text)
    return text


def label(value):
    return redact(value)[:160]


def fingerprint(value):
    # Hash only after redaction, never serialize the original value.
    normalized = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(redact(normalized).encode()).hexdigest()


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError("timestamp required")
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("timestamp requires timezone")
    return dt


FIELDS = {"schema_version", "id", "task_id", "agent", "timestamp", "kind", "status",
          "model", "input_tokens", "output_tokens", "cached_tokens", "cache_write_tokens",
          "amount", "currency", "origin", "category", "duration_ms", "queue_ms", "human_wait_ms",
          "action", "signature", "context_signature", "progress", "retry_reason", "synthetic", "source_line"}


def event(data):
    if data.get("schema_version") != VERSION:
        raise ValueError("unsupported event schema_version")
    required = ("id", "task_id", "agent", "timestamp", "kind")
    if any(not data.get(k) for k in required):
        raise ValueError("missing required event fields")
    timestamp(data["timestamp"])
    if data["kind"] not in {"model", "tool", "human", "wait", "task"}:
        raise ValueError("unsupported event kind")
    result = {k: v for k, v in data.items() if k in FIELDS and v is not None and v != ""}
    for k in ("id", "task_id", "agent", "model", "action"):
        if k in result:
            result[k] = label(result[k])
    for k in ("signature", "context_signature"):
        if k in result and not re.fullmatch(r"[a-f0-9]{64}", str(result[k])):
            result[k] = fingerprint(result[k])
    for k in ("input_tokens", "output_tokens", "cached_tokens", "cache_write_tokens", "duration_ms", "queue_ms", "human_wait_ms", "source_line"):
        if k in result:
            value = result[k]
            if isinstance(value, bool) or not re.fullmatch(r"\d+", str(value)):
                raise ValueError("counts must be nonnegative integers")
            result[k] = int(value)
    if result.get("cached_tokens", 0) + result.get("cache_write_tokens", 0) > result.get("input_tokens", 0):
        raise ValueError("cache tokens exceed inclusive input tokens")
    if "amount" in result:
        result["amount"] = str(money(result["amount"]))
        if result.get("origin") not in {"actual", "estimated", "manual"}:
            raise ValueError("amount requires origin")
        if not re.fullmatch(r"[A-Z]{3}", str(result.get("currency", ""))):
            raise ValueError("amount requires ISO-style currency")
    if "origin" in result and result["origin"] not in {"actual", "estimated", "manual"}:
        raise ValueError("invalid cost origin")
    if "currency" in result and not re.fullmatch(r"[A-Z]{3}", str(result["currency"])):
        raise ValueError("invalid currency")
    if result.get("status", "unknown") not in {"success", "failed", "timeout", "unknown", "running"}:
        raise ValueError("invalid status")
    if result.get("category", "model") not in {"model", "tool", "failure", "rework", "wait", "quality"}:
        raise ValueError("invalid category")
    if result.get("retry_reason", "unknown") not in {"unknown", "transient", "user_requested", "idempotent_check"}:
        raise ValueError("invalid retry reason")
    for k in ("synthetic", "progress"):
        if k in result and not isinstance(result[k], bool):
            if result[k] not in ("true", "false"):
                raise ValueError("invalid boolean")
            result[k] = result[k] == "true"
    return result


def tasks_validate(tasks):
    allowed = {"task_id", "agent", "task_key", "difficulty", "acceptance_id", "status", "accepted",
               "baseline_minutes", "human_minutes", "rework_minutes", "hourly_rate", "currency", "baseline_verified", "synthetic",
               "model", "prompt_strategy", "workflow"}
    result = []
    seen = set()
    normalized_ids = set()
    for item in tasks:
        if not item.get("task_id") or item["task_id"] in seen:
            raise ValueError("task ids required and unique")
        seen.add(item["task_id"])
        task = {k: v for k, v in item.items() if k in allowed and v is not None}
        for k in ("task_id", "agent", "task_key", "difficulty", "acceptance_id", "model", "prompt_strategy", "workflow"):
            if k in task:
                task[k] = label(task[k])
        for k in ("baseline_minutes", "human_minutes", "rework_minutes", "hourly_rate"):
            if k in task:
                task[k] = str(money(task[k]))
        for k in ("accepted", "baseline_verified", "synthetic"):
            if k in task and not isinstance(task[k], bool):
                raise ValueError("task booleans must be JSON booleans")
        if task.get("status", "unknown") not in {"success", "failed", "running", "unknown"}:
            raise ValueError("invalid task status")
        if "hourly_rate" in task and not re.fullmatch(r"[A-Z]{3}", task.get("currency", "")):
            raise ValueError("hourly rate requires currency")
        if "currency" in task and not re.fullmatch(r"[A-Z]{3}", task["currency"]):
            raise ValueError("invalid currency")
        if task["task_id"] in normalized_ids:
            raise ValueError("task ids collide after privacy normalization")
        normalized_ids.add(task["task_id"])
        result.append(task)
    return result
