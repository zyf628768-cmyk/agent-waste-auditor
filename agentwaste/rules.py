"""Explicit, reproducible heuristic thresholds; currencies never imply FX."""
from dataclasses import dataclass, field, asdict
from .models import money
from .schemas import CURRENCY, validate


@dataclass(frozen=True)
class Rules:
    repetition_threshold: int = 3
    window_seconds: int = 3600
    context_tokens: int = 10000
    high_cost_thresholds: dict = field(default_factory=lambda: {"USD": "1"})

    @classmethod
    def from_dict(cls, data=None):
        if data is None:
            return cls()
        if not isinstance(data, dict) or data.get("schema_version") != "1.0":
            raise ValueError("unsupported rules configuration")
        allowed = {"schema_version", "repetition_threshold", "window_seconds", "context_tokens", "high_cost_thresholds"}
        if set(data) - allowed:
            raise ValueError("unknown rule setting")
        values = {k: v for k, v in data.items() if k != "schema_version"}
        for key, minimum, maximum in (("repetition_threshold", 3, 1000), ("window_seconds", 1, 31_536_000), ("context_tokens", 1, 10**15)):
            if key in values and (type(values[key]) is not int or not minimum <= values[key] <= maximum):
                raise ValueError("invalid rule threshold")
        if "high_cost_thresholds" in values:
            thresholds = values["high_cost_thresholds"]
            if not isinstance(thresholds, dict):
                raise ValueError("currency threshold map required")
            for cur, amount in thresholds.items():
                validate(cur, CURRENCY)
                if not money(amount):
                    raise ValueError("high cost threshold must be positive")
            values["high_cost_thresholds"] = {cur: str(money(amount)) for cur, amount in thresholds.items()}
        return cls(**values)

    def describe(self):
        return {"schema_version": "1.0", **asdict(self)}
