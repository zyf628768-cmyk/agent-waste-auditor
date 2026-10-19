from ..models import event, fingerprint, label
from ..safeio import InputError


def convert(rows):
    events = []
    identities = {field: {} for field in ("task_id", "agent", "model")}
    for line, row in rows:
        row = dict(row)
        for field, seen in identities.items():
            raw = row.get(field)
            if raw is not None and raw != "":
                normalized = label(raw)
                if normalized in seen and seen[normalized] != raw:
                    raise InputError("IDENTITY_COLLISION", line)
                seen[normalized] = raw
        # Never persist raw arguments/file names. Evidence uses stable digests.
        if row.get("arguments"):
            row["signature"] = fingerprint([row.get("action"), row["arguments"]])
        row["source_line"] = line
        try:
            events.append(event(row))
        except ValueError as exc:
            raise ValueError(f"invalid generic event at line {line}: {exc}") from None
    return events, ([] if events else ["EMPTY_INPUT"]), "agentwaste-1.0"
