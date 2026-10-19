"""Verify the installed distribution outside the checkout, without private logs."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "docs/installation-evidence.json")
    args = parser.parse_args()
    results = []
    with tempfile.TemporaryDirectory(prefix="agentwaste-smoke-") as tmp:
        tmp = Path(tmp)
        p = subprocess.run([sys.executable, "-c", "import agentwaste; print(agentwaste.__file__)"], cwd=tmp, capture_output=True, text=True)
        if p.returncode or Path(p.stdout.strip()).resolve().is_relative_to(ROOT.resolve()):
            raise RuntimeError("install the wheel outside the source checkout before smoke validation")
        commands = [["--version"], ["import", str(ROOT / "examples/success.jsonl"), "--tasks", str(ROOT / "examples/success.tasks.json"), "-o", str(tmp / "events.json")],
                    ["analyze", str(tmp / "events.json"), "--pricing", str(ROOT / "examples/pricing.json"), "-o", str(tmp / "audit.json")],
                    ["compare", str(tmp / "events.json"), "--pricing", str(ROOT / "examples/pricing.json"), "-o", str(tmp / "comparison.json")],
                    ["pricing", str(ROOT / "examples/pricing.json")],
                    ["doctor", "--input", str(ROOT / "examples/success.jsonl"), "--pricing", str(ROOT / "examples/pricing.json")]]
        commands.extend([["report", str(tmp / "audit.json"), "--format", f, "-o", str(tmp / ("report." + f))] for f in ("json", "html", "markdown", "csv")])
        commands.extend([["report", str(tmp / "comparison.json"), "--format", "csv", "-o", str(tmp / "comparison.csv")]])
        commands.extend([[c, "--help"] for c in ("import", "analyze", "compare", "report", "pricing", "doctor")])
        for command in commands:
            p = subprocess.run([sys.executable, "-m", "agentwaste", *command], cwd=tmp, capture_output=True, text=True, encoding="utf-8")
            result = {"command": "agentwaste " + " ".join(command).replace(str(ROOT), "PROJECT").replace(str(tmp), "TEMP_OUTPUT"), "exit_code": p.returncode, "stdout": p.stdout, "stderr": p.stderr}
            results.append(result)
            if p.returncode:
                raise RuntimeError("installed CLI smoke failed; check structured evidence")
        if "per_attempt" not in (tmp / "comparison.csv").read_text():
            raise RuntimeError("comparison CSV is missing normalized metrics")
    evidence = {"installed_wheel": "agent_waste_auditor-0.1.0-py3-none-any.whl", "isolated_target_import": True,
                "passed_commands": len(results), "results": results}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"passed_commands": len(results), "isolated_target_import": True}))


if __name__ == "__main__":
    main()
