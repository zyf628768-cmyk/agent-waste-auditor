"""Date-bounded, user-supplied prices. No network or guessed model prices."""
from datetime import date, timezone
from bisect import bisect_right
import re
from .models import money, timestamp, label, redact, financial


class PriceBook:
    def __init__(self, data=None):
        data = {"schema_version": "1.0", "prices": []} if data is None else data
        if not isinstance(data, dict) or data.get("schema_version") != "1.0":
            raise ValueError("unsupported pricing schema")
        if not isinstance(data.get("prices"), list):
            raise ValueError("prices must be an array")
        self.prices = []
        self._models = {}
        seen, normalized_seen, raw_models = set(), set(), {}
        fields = {"id", "model", "currency", "source", "effective_from", "effective_to", "input_per_million", "output_per_million", "cache_read_per_million", "cache_write_per_million"}
        for row in data["prices"]:
            if not isinstance(row, dict):
                raise ValueError("price entry must be an object")
            p = {k: v for k, v in row.items() if k in fields}
            if not all(p.get(k) for k in ("id", "model", "currency", "effective_from", "effective_to", "source")):
                raise ValueError("incomplete price provenance")
            if p["id"] in seen or not re.fullmatch(r"[A-Z]{3}", p["currency"]):
                raise ValueError("invalid price id/currency")
            seen.add(p["id"])
            for key in ("id", "model"):
                p[key] = label(p[key])
            if p["id"] in normalized_seen:
                raise ValueError("price ids collide after privacy normalization")
            normalized_seen.add(p["id"])
            if p["model"] in raw_models and raw_models[p["model"]] != row["model"]:
                raise ValueError("price model identities collide after redaction")
            raw_models[p["model"]] = row["model"]
            if not isinstance(p["source"], str) or len(p["source"]) > 2048:
                raise ValueError("invalid price source")
            p["source"] = redact(p["source"])
            for key in ("effective_from", "effective_to"):
                parsed = date.fromisoformat(p[key]).isoformat()
                if parsed != p[key]:
                    raise ValueError("pricing date must be YYYY-MM-DD")
            if date.fromisoformat(p["effective_from"]) > date.fromisoformat(p["effective_to"]):
                raise ValueError("invalid pricing date range")
            for key in ("input_per_million", "output_per_million", "cache_read_per_million", "cache_write_per_million"):
                if key in p:
                    p[key] = str(money(p[key]))
            if not all(k in p for k in ("input_per_million", "output_per_million")):
                raise ValueError("input/output rates required")
            self.prices.append(p)
            self._models.setdefault(p["model"], []).append(p)
        for model, entries in self._models.items():
            entries.sort(key=lambda p: p["effective_from"])
            for p, q in zip(entries, entries[1:]):
                if q["effective_from"] <= p["effective_to"]:
                    raise ValueError("overlapping price windows for model")
        self._dates = {model: [p["effective_from"] for p in entries] for model, entries in self._models.items()}

    @financial
    def estimate(self, e):
        if e.get("usage_complete") is False:
            return None, "TOKEN_USAGE_INCOMPLETE"
        d = timestamp(e["timestamp"]).astimezone(timezone.utc).date().isoformat()
        entries = self._models.get(e.get("model"), [])
        index = bisect_right(self._dates.get(e.get("model"), []), d) - 1
        if index < 0 or d > entries[index]["effective_to"]:
            return None, "PRICE_MISSING_OR_EXPIRED"
        p = entries[index]
        if not all(k in e for k in ("input_tokens", "output_tokens", "cached_tokens")):
            return None, "TOKEN_USAGE_INCOMPLETE"
        cached, writes = e["cached_tokens"], e.get("cache_write_tokens", 0)
        if (cached and "cache_read_per_million" not in p) or (writes and "cache_write_per_million" not in p):
            return None, "CACHE_PRICE_UNAVAILABLE"
        amount = (money(p["input_per_million"]) * (e["input_tokens"] - cached - writes)
                  + money(p["output_per_million"]) * e["output_tokens"]
                  + money(p.get("cache_read_per_million", 0)) * cached
                  + money(p.get("cache_write_per_million", 0)) * writes) / 1_000_000
        return {"amount": str(amount), "currency": p["currency"], "origin": "estimated", "price_id": p["id"]}, None
