import argparse
import json
import sys
from pathlib import Path
from . import __version__
from .importers.base import import_file, dataset, load
from .models import tasks_validate
from .pricing import PriceBook
from .costs import analyze
from .compare import compare
from .reports import write
from .doctor import check
from .safeio import InputError
from .schemas import validate_report
from .rules import Rules


def parser():
    p = argparse.ArgumentParser(prog="agentwaste", description="Offline AI task cost audit. Explicit files only.")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="command", required=True)
    imp = sub.add_parser("import", help="Import one explicitly specified log; discard private payloads")
    imp.add_argument("input", type=Path)
    imp.add_argument("--format", choices=["jsonl", "csv", "codex", "claude", "openai"], default="jsonl")
    imp.add_argument("--tasks", type=Path, help="JSON array of user-entered task economics")
    imp.add_argument("-o", "--output", required=True, type=Path)
    a = sub.add_parser("analyze", help="Analyze canonical dataset with optional dated prices")
    a.add_argument("input", type=Path)
    a.add_argument("--pricing", type=Path)
    a.add_argument("--rules", type=Path, help="Versioned heuristic thresholds; no remote configuration")
    a.add_argument("-o", "--output", required=True, type=Path)
    c = sub.add_parser("compare", help="Compare canonical datasets in matching acceptance groups")
    c.add_argument("inputs", nargs="+", type=Path)
    c.add_argument("--pricing", type=Path)
    c.add_argument("--rules", type=Path)
    c.add_argument("--by", choices=["agent", "model", "prompt_strategy", "workflow"], default="agent")
    c.add_argument("-o", "--output", required=True, type=Path)
    r = sub.add_parser("report", help="Render audit/comparison JSON as offline reports")
    r.add_argument("input", type=Path)
    r.add_argument("--format", choices=["json", "csv", "markdown", "html"], default="html")
    r.add_argument("-o", "--output", required=True, type=Path)
    prices = sub.add_parser("pricing", help="Validate and show user supplied dated pricing; no network")
    prices.add_argument("input", nargs="?", type=Path)
    d = sub.add_parser("doctor", help="Read-only runtime, explicit log and configuration checks")
    d.add_argument("--input", type=Path)
    d.add_argument("--format", choices=["jsonl", "csv", "codex", "claude", "openai"], default="jsonl")
    d.add_argument("--pricing", type=Path)
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        # Output must never overwrite any explicitly supplied input.
        sources = [getattr(args, k, None) for k in ("input", "tasks", "pricing", "rules")]
        sources.extend(getattr(args, "inputs", []))
        if getattr(args, "output", None) and any(isinstance(s, Path) and s.resolve() == args.output.resolve() for s in sources):
            raise ValueError("output must differ from source files")
        if getattr(args, "output", None) and args.output.exists() and any(isinstance(s, Path) and s.exists() and s.samefile(args.output) for s in sources):
            raise ValueError("output aliases a source file")
        if args.command == "import":
            result = import_file(args.input, args.format)
            if args.tasks:
                result["tasks"] = tasks_validate(load(args.tasks))
        elif args.command in {"analyze", "compare"}:
            book = PriceBook(load(args.pricing) if args.pricing else None)
            rules = Rules.from_dict(load(args.rules) if args.rules else None)
            if args.command == "analyze":
                result = analyze(dataset(args.input), book, rules)
            else:
                result = compare([analyze(dataset(path), book, rules) for path in args.inputs], args.by)
        elif args.command == "report":
            # Reports should be our structured output, not a raw arbitrary JSON object.
            result = load(args.input)
            validate_report(result)
            write(result, args.output, args.format)
            print("Report written")
            return 0
        elif args.command == "pricing":
            result = {"schema_version": "1.0", "prices": PriceBook(load(args.input) if args.input else None).prices,
                      "notice": "No bundled commercial model prices; explicit provenance and date windows required."}
            # Price source fields are configuration text; keep secrets out of console.
            print(json.dumps(result, indent=2))
            return 0
        else:
            result = check(args.input, args.format, args.pricing)
            print(json.dumps(result, indent=2))
            return 0 if result["ok"] else 1
        write(result, args.output)
        print("Written " + args.command + " result")
        return 0
    except InputError as exc:
        suffix = f" at source line {exc.line}" if exc.line else ""
        print(f"agentwaste: {exc.code}{suffix}", file=sys.stderr)
        return 2
    except (ValueError, OSError, KeyError, TypeError, ArithmeticError, AttributeError, RecursionError):
        # No exception repr: malformed inputs and file names may contain credentials.
        print("agentwaste: invalid/incompatible input or inaccessible output; check documented schema and doctor", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
