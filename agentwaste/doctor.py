import importlib.util
import platform
import sys
from .importers.base import import_file


def check(input=None, format="jsonl", pricing=None):
    checks = [{"check": "python_3_11", "ok": sys.version_info >= (3, 11), "detail": platform.python_version()},
              {"check": "runtime_dependencies", "ok": True, "detail": "standard library only"}]
    checks.append({"check": "jsonschema_optional", "ok": True, "available": importlib.util.find_spec("jsonschema") is not None})
    if pricing:
        from .pricing import PriceBook
        from .importers.base import load
        try:
            book = PriceBook(load(pricing))
            checks.append({"check": "pricing", "ok": True, "entries": len(book.prices)})
        except (ValueError, OSError, KeyError, TypeError):
            checks.append({"check": "pricing", "ok": False, "detail": "invalid pricing configuration"})
    if input:
        try:
            data = import_file(input, format)
            checks.append({"check": "log_compatibility", "ok": bool(data["events"]), "profile": data["profile"], "warnings": data["warnings"]})
        except (ValueError, OSError, KeyError, TypeError, OverflowError):
            checks.append({"check": "log_compatibility", "ok": False, "detail": "invalid or incompatible log"})
    return {"read_only": True, "ok": all(c["ok"] for c in checks), "checks": checks}
