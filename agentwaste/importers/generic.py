from ..models import event, fingerprint


def convert(rows):
    events = []
    for line, row in rows:
        row = dict(row)
        # Never persist raw arguments/file names. Evidence uses stable digests.
        if row.get("arguments"):
            row["signature"] = fingerprint([row.get("action"), row["arguments"]])
        row["source_line"] = line
        try:
            events.append(event(row))
        except ValueError as exc:
            raise ValueError(f"invalid generic event at line {line}: {exc}") from None
    return events, ([] if events else ["EMPTY_INPUT"]), "agentwaste-1.0"
