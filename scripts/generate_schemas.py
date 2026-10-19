"""Export the exact schemas used by runtime report validation."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agentwaste.schemas import SCHEMAS


def main():
    destination = ROOT / "schemas"
    destination.mkdir(exist_ok=True)
    for name, definition in SCHEMAS.items():
        schema = {"$schema": "https://json-schema.org/draft/2020-12/schema",
                  "$id": f"https://agentwaste.invalid/schemas/{name}.schema.json", **definition}
        (destination / f"{name}.schema.json").write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("Schemas generated from runtime definitions")


if __name__ == "__main__":
    main()
