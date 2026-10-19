"""Execute real tests and record counts without claiming unexecuted platforms."""
import json
from pathlib import Path
import platform
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    tests = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    log = ROOT / "docs" / "test-results.txt"
    with log.open("w", encoding="utf-8") as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(tests)
    data = {"date": "2026-10-19", "python": platform.python_version(), "os": platform.system(),
            "tests": result.testsRun, "passed": result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped),
            "failures": len(result.failures), "errors": len(result.errors), "skipped": len(result.skipped),
            "github_matrix_executed": False}
    (ROOT / "docs" / "validation-results.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(data, indent=2))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
