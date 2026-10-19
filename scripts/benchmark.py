"""Measure a declared SYNTHETIC workload; no fragile timing pass threshold."""
import argparse
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
from pathlib import Path
import platform
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agentwaste.costs import analyze
from agentwaste.pricing import PriceBook
from agentwaste.importers.base import load


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", type=int, default=10000)
    parser.add_argument("--output", type=Path, default=ROOT / "docs/performance.json")
    args = parser.parse_args()
    if not 1 <= args.events <= 100000:
        parser.error("events must be between 1 and 100000")
    events = []
    base = datetime(2026, 10, 1, tzinfo=timezone.utc)
    models = 0
    for i in range(args.events):
        e = {"schema_version": "1.0", "id": f"SYNTHETIC-{i}", "task_id": f"SYNTHETIC-task-{i % 100}",
             "agent": "SYNTHETIC-agent", "timestamp": (base + timedelta(minutes=i * 10)).isoformat(), "synthetic": True}
        if i % 5 == 0:
            e.update(kind="tool", amount="0", origin="actual", currency="USD", action="SYNTHETIC-check")
        else:
            e.update(kind="model", model="SYNTHETIC-model", input_tokens=1000, output_tokens=200, cached_tokens=400)
            models += 1
        events.append(e)
    start = perf_counter()
    price_data = load(ROOT / "examples/pricing.json")
    price_data["prices"][0]["effective_to"] = "2030-12-31"
    r = analyze({"events": events, "tasks": [], "warnings": []}, PriceBook(price_data))
    elapsed = perf_counter() - start
    expected = Decimal("0.003") * models
    if r["coverage"]["events"] != args.events or Decimal(r["totals"]["USD"]["estimated"]) != expected:
        raise RuntimeError("SYNTHETIC benchmark financial invariant failed")
    if len(r["tasks"]) != min(args.events, 100):
        raise RuntimeError("SYNTHETIC task identity invariant failed")
    result = {"synthetic": True, "python": platform.python_version(), "os": platform.system(), "events": args.events,
              "tasks": len(r["tasks"]), "analysis_seconds": round(elapsed, 6), "events_per_second": round(args.events / elapsed, 1),
              "expected_estimated_usd": str(expected), "observed_estimated_usd": r["totals"]["USD"]["estimated"],
              "financial_invariant_passed": True, "note": "One local measurement, not a cross-machine performance guarantee; no raw prompts or user data."}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
