import csv
import json
from pathlib import Path
from ..models import VERSION, event, tasks_validate


def read_records(path, csv_mode=False):
    path = Path(path)
    if path.stat().st_size > 100_000_000:
        raise ValueError("input exceeds 100 MB limit; split explicitly")
    with path.open(encoding="utf-8-sig", newline="") as stream:
        if csv_mode:
            return [(i, row) for i, row in enumerate(csv.DictReader(stream), 2)]
        rows = []
        for i, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line, parse_float=str)
            except (ValueError, TypeError):
                raise ValueError(f"invalid JSON at line {i}") from None
            if not isinstance(row, dict):
                raise ValueError(f"object required at line {i}")
            rows.append((i, row))
        return rows


def load(path):
    with Path(path).open(encoding="utf-8-sig") as stream:
        return json.load(stream, parse_float=str)


def import_file(path, format="jsonl"):
    from . import generic, codex, claude, openai
    rows = read_records(path, format == "csv")
    adapter = {"jsonl": generic, "csv": generic, "codex": codex, "claude": claude, "openai": openai}[format]
    events, warnings, profile = adapter.convert(rows)
    seen = set()
    for e in events:
        if e["id"] in seen:
            raise ValueError("duplicate canonical event id")
        seen.add(e["id"])
    return {"schema_version": VERSION, "source_format": format, "profile": profile,
            "source_records": len(rows), "events": events, "tasks": [], "warnings": warnings}


def dataset(path):
    data = load(path)
    if data.get("schema_version") != VERSION:
        raise ValueError("unsupported dataset version")
    data["events"] = [event(e) for e in data["events"]]
    ids = [e["id"] for e in data["events"]]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate event id")
    data["tasks"] = tasks_validate(data.get("tasks", []))
    # Retain only generated diagnostic codes, not arbitrary untrusted prose.
    data["warnings"] = [w for w in data.get("warnings", []) if isinstance(w, str) and w.replace("_", "").isalnum()]
    return {k: data[k] for k in ("schema_version", "events", "tasks", "warnings")}
