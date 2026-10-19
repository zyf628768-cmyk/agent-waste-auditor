"""Reproduce all SYNTHETIC demos using the public CLI. Offline and deterministic."""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def run(args):
    p = subprocess.run([sys.executable, "-m", "agentwaste", *map(str, args)], cwd=ROOT,
                       capture_output=True, text=True)
    evidence = {"command": "agentwaste " + " ".join(map(str, args)), "exit_code": p.returncode,
                "stdout": p.stdout.strip(), "stderr": p.stderr.strip()}
    if p.returncode:
        raise RuntimeError(json.dumps(evidence))
    return evidence


def main():
    out = ROOT / "examples" / "reports"
    out.mkdir(exist_ok=True)
    evidence = []
    prices = "examples/pricing.json"
    for command in ("import", "analyze", "compare", "report", "pricing", "doctor"):
        evidence.append(run([command, "--help"]))
    for name in ("success", "waste", "claude"):
        canonical = f"examples/reports/{name}.events.json"
        audit = f"examples/reports/{name}.audit.json"
        evidence.append(run(["import", f"examples/{name}.jsonl", "--tasks", f"examples/{name}.tasks.json", "-o", canonical]))
        evidence.append(run(["analyze", canonical, "--pricing", prices, "-o", audit]))
        for format, ext in (("html", "html"), ("markdown", "md"), ("csv", "csv")):
            evidence.append(run(["report", audit, "--format", format, "-o", f"examples/reports/{name}.{ext}"]))
    comparison = "examples/reports/comparison.json"
    evidence.append(run(["compare", "examples/reports/success.events.json", "examples/reports/claude.events.json", "--pricing", prices, "-o", comparison]))
    for format, ext in (("html", "html"), ("markdown", "md"), ("csv", "csv")):
        evidence.append(run(["report", comparison, "--format", format, "-o", f"examples/reports/comparison.{ext}"]))
    evidence.append(run(["pricing", prices]))
    evidence.append(run(["doctor", "--input", "examples/success.jsonl", "--pricing", prices]))
    evidence.append(run(["import", "examples/success.csv", "--format", "csv", "-o", "examples/reports/csv.events.json"]))
    evidence.append(run(["analyze", "examples/reports/waste.events.json", "--pricing", prices, "--rules", "examples/rules.json", "-o", "examples/reports/waste.custom-rules.json"]))
    for name, fmt in (("codex-native", "codex"), ("claude-native", "claude"), ("openai-native", "openai")):
        evidence.append(run(["import", f"examples/{name}.jsonl", "--format", fmt, "-o", f"examples/reports/{name}.events.json"]))
    (out / "cli-evidence.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8", newline="\n")
    summary = {}
    for name in ("success", "waste", "claude"):
        r = json.loads((out / f"{name}.audit.json").read_text(encoding="utf-8"))
        summary[name] = {"totals": r["totals"], "findings": len(r["findings"]), "rules": sorted({f["rule"] for f in r["findings"]}), "roi": r["tasks"][0]["roi"]}
    (out / "demo-summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
