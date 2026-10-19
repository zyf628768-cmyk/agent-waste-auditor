import csv
import io
from pathlib import Path
from ..models import VERSION, event, tasks_validate
from ..safeio import MAX_BYTES, MAX_LINE_BYTES, InputError, parse_json, load_json

DIAGNOSTICS = {"EMPTY_INPUT", "CACHE_USAGE_UNAVAILABLE", "TOKEN_USAGE_INCOMPLETE", "EXPERIMENTAL_CODEX_PROFILE",
               "EXPERIMENTAL_CLAUDE_PROFILE", "NATIVE_TASK_OUTCOME_UNAVAILABLE", "VERSION_UNAVAILABLE",
               "CUMULATIVE_USAGE_UNAVAILABLE", "UNMATCHED_TOOL_OUTPUT", "NO_SUPPORTED_EVENTS",
               "UNSUPPORTED_NATIVE_RECORDS", "USAGE_GAP", "AMBIGUOUS_MODEL_USAGE"}


def read_records(path, csv_mode=False):
    with Path(path).open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise InputError("INPUT_SIZE_LIMIT")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeError:
        raise InputError("INPUT_NOT_UTF8") from None
    if csv_mode:
        if not text.strip():
            return []
        reader = csv.reader(io.StringIO(text, newline=""), strict=True)
        try:
            headers = next(reader)
            if not headers or any(not h for h in headers) or len(headers) != len(set(headers)):
                raise InputError("INVALID_CSV_HEADERS", 1)
            rows = []
            for values in reader:
                if not values:
                    continue
                if len(values) != len(headers):
                    raise InputError("INVALID_CSV_ROW", reader.line_num)
                rows.append((reader.line_num, dict(zip(headers, values))))
            return rows
        except csv.Error:
            raise InputError("INVALID_CSV", reader.line_num) from None
    rows = []
    for i, line in enumerate(text.split('\n'), 1):
        if not line.strip():
            continue
        if len(line.encode("utf-8")) > MAX_LINE_BYTES:
            raise InputError("LINE_SIZE_LIMIT", i)
        row = parse_json(line, i)
        if not isinstance(row, dict):
            raise InputError("JSON_OBJECT_REQUIRED", i)
        rows.append((i, row))
    return rows


def load(path):
    return load_json(path)


def import_file(path, format="jsonl"):
    from . import generic, codex, claude, openai
    rows = read_records(path, format == "csv")
    adapter = {"jsonl": generic, "csv": generic, "codex": codex, "claude": claude, "openai": openai}[format]
    events, warnings, profile = adapter.convert(rows)
    seen = set()
    for e in events:
        if e["id"] in seen:
            raise InputError("DUPLICATE_EVENT_ID")
        seen.add(e["id"])
    return {"schema_version": VERSION, "source_format": format, "profile": profile,
            "source_records": len(rows), "events": events, "tasks": [], "warnings": warnings}


def dataset(path):
    data = load(path)
    if not isinstance(data, dict) or data.get("schema_version") != VERSION:
        raise ValueError("unsupported dataset version")
    if not isinstance(data.get("events"), list):
        raise InputError("EVENT_ARRAY_REQUIRED")
    data["events"] = [event(e) for e in data["events"]]
    ids = [e["id"] for e in data["events"]]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate event id")
    data["tasks"] = tasks_validate(data.get("tasks", []))
    # Retain only generated diagnostic codes, not arbitrary untrusted prose.
    if not isinstance(data.get("warnings", []), list):
        raise InputError("WARNING_ARRAY_REQUIRED")
    data["warnings"] = sorted({w for w in data.get("warnings", []) if isinstance(w, str) and w in DIAGNOSTICS})
    return {k: data[k] for k in ("schema_version", "events", "tasks", "warnings")}
