"""Date-bounded, user-supplied prices. No network or guessed model prices."""
from datetime import date
import re
from .models import money, timestamp


class PriceBook:
    def __init__(self, data=None):
        data = data or {"schema_version": "1.0", "prices": []}
        if data.get("schema_version") != "1.0":
            raise ValueError("unsupported pricing schema")
        self.prices = data["prices"]
        seen = set()
        for p in self.prices:
            if not all(p.get(k) for k in ("id", "model", "currency", "effective_from", "effective_to", "source")):
                raise ValueError("incomplete price provenance")
            if p["id"] in seen or not re.fullmatch(r"[A-Z]{3}", p["currency"]):
                raise ValueError("invalid price id/currency")
            seen.add(p["id"])
            if date.fromisoformat(p["effective_from"]) > date.fromisoformat(p["effective_to"]):
                raise ValueError("invalid pricing date range")
            for key in ("input_per_million", "output_per_million", "cache_read_per_million", "cache_write_per_million"):
                if key in p:
                    money(p[key])
            if not all(k in p for k in ("input_per_million", "output_per_million")):
                raise ValueError("input/output rates required")
        for i, p in enumerate(self.prices):
            for q in self.prices[i + 1:]:
                if p["model"] == q["model"] and max(p["effective_from"], q["effective_from"]) <= min(p["effective_to"], q["effective_to"]):
                    raise ValueError("overlapping price windows for model")

    def estimate(self, e):
        d = timestamp(e["timestamp"]).date().isoformat()
        matches = [p for p in self.prices if p["model"] == e.get("model") and p["effective_from"] <= d <= p["effective_to"]]
        if not matches:
            return None, "PRICE_MISSING_OR_EXPIRED"
        p = matches[0]
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
