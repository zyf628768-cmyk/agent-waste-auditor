"""Bounded input and atomic local output; errors never contain source values."""
import json
import os
from pathlib import Path
import tempfile

MAX_BYTES = 100_000_000
MAX_LINE_BYTES = 4_000_000
MAX_DEPTH = 40


class InputError(ValueError):
    def __init__(self, code, line=None):
        self.code = code
        self.line = line
        super().__init__(code)


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InputError("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def reject_constant(value):
    raise InputError("NONFINITE_JSON_NUMBER")


def check_depth(value):
    pending = [(value, 0)]
    while pending:
        value, depth = pending.pop()
        if depth > MAX_DEPTH:
            raise InputError("NESTING_LIMIT")
        if isinstance(value, dict):
            pending.extend((v, depth + 1) for v in value.values())
        elif isinstance(value, list):
            pending.extend((v, depth + 1) for v in value)


def parse_json(text, line=None):
    try:
        value = json.loads(text, parse_float=str, object_pairs_hook=unique_pairs, parse_constant=reject_constant)
        check_depth(value)
        return value
    except InputError as exc:
        raise InputError(exc.code, line) from None
    except (ValueError, RecursionError):
        raise InputError("INVALID_JSON", line) from None


def load_json(path):
    with Path(path).open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise InputError("INPUT_SIZE_LIMIT")
    try:
        return parse_json(raw.decode("utf-8-sig"))
    except UnicodeError:
        raise InputError("INPUT_NOT_UTF8") from None


def atomic_write(path, content):
    """Render fully before replacing an existing report; cleanup on failure."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="", dir=target.parent,
                                         prefix=".agentwaste-", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
