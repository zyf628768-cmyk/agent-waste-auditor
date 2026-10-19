import copy
import csv
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

import jsonschema

from agentwaste.models import event, money, fingerprint, redact, tasks_validate
from agentwaste.importers.base import import_file, dataset
from agentwaste.pricing import PriceBook
from agentwaste.costs import analyze
from agentwaste.waste import detect
from agentwaste.compare import compare
from agentwaste.reports import write
from agentwaste.cli import main
from agentwaste.doctor import check
from agentwaste.importers import codex, claude, openai

ROOT = Path(__file__).resolve().parents[1]


def sample(**kwargs):
    data = dict(schema_version="1.0", id="e1", task_id="t1", agent="codex", timestamp="2026-10-01T01:00:00Z",
                kind="model", model="SYNTHETIC-model", input_tokens=1000, output_tokens=200,
                cached_tokens=400, synthetic=True)
    data.update(kwargs)
    return event(data)


def prices(**kwargs):
    row = dict(id="SYNTHETIC-v1", model="SYNTHETIC-model", currency="USD", source="SYNTHETIC",
               effective_from="2026-01-01", effective_to="2026-12-31", input_per_million="2",
               output_per_million="8", cache_read_per_million="0.5", cache_write_per_million="3")
    row.update(kwargs)
    return PriceBook({"schema_version": "1.0", "prices": [row]})


def data(events=None, tasks=None):
    return dict(schema_version="1.0", events=events if events is not None else [sample()], tasks=tasks or [], warnings=[])


def task(**kwargs):
    t = dict(task_id="t1", agent="codex", status="success", accepted=True, baseline_minutes="60",
             human_minutes="10", rework_minutes="5", hourly_rate="60", currency="USD", baseline_verified=True,
             task_key="SYNTHETIC-unit", difficulty="easy", acceptance_id="SYNTHETIC-tests-v1", synthetic=True)
    t.update(kwargs)
    return t


class Costs(unittest.TestCase):
    def test_decimal_cache_read(self):
        c, err = prices().estimate(sample())
        self.assertIsNone(err)
        self.assertEqual(c["amount"], "0.003")

    def test_cache_write_separate(self):
        c, _ = prices().estimate(sample(cache_write_tokens=100))
        self.assertEqual(c["amount"], "0.0031")

    def test_cache_price_missing(self):
        book = prices()
        del book.prices[0]["cache_read_per_million"]
        self.assertEqual(book.estimate(sample())[1], "CACHE_PRICE_UNAVAILABLE")

    def test_missing_price(self):
        self.assertEqual(prices().estimate(sample(model="unknown"))[1], "PRICE_MISSING_OR_EXPIRED")

    def test_expired_price(self):
        self.assertEqual(prices(effective_to="2026-09-01").estimate(sample())[1], "PRICE_MISSING_OR_EXPIRED")

    def test_missing_usage_is_unknown(self):
        e = sample()
        del e["output_tokens"]
        self.assertEqual(prices().estimate(e)[1], "TOKEN_USAGE_INCOMPLETE")

    def test_cache_unknown_not_assumed_zero(self):
        e = sample()
        del e["cached_tokens"]
        self.assertEqual(prices().estimate(e)[1], "TOKEN_USAGE_INCOMPLETE")

    def test_actual_takes_precedence(self):
        report = analyze(data([sample(amount="1.25", origin="actual", currency="EUR")]), prices())
        self.assertEqual(report["totals"], {"EUR": {"actual": "1.25", "estimated": "0", "manual": "0"}})

    def test_failure_not_free(self):
        report = analyze(data([sample(status="failed")], [task(status="failed", accepted=False)]), prices())
        self.assertEqual(report["tasks"][0]["failed_step_costs"]["USD"]["estimated"], "0.003")
        self.assertIsNone(report["average_cost_per_success"])

    def test_human_rework(self):
        t = analyze(data(tasks=[task()]), prices())["tasks"][0]
        self.assertEqual(t["totals"]["USD"]["manual"], "15")
        self.assertEqual(t["category_totals"]["rework"]["USD"]["manual"], "5")

    def test_wait_not_wages(self):
        r = analyze(data([sample(kind="wait", duration_ms=3_600_000, human_wait_ms=1000)]), prices())
        self.assertEqual(r["totals"], {})
        self.assertEqual(r["tasks"][0]["human_wait_ms"], 1000)

    def test_roi_missing_baseline(self):
        r = analyze(data(), prices())
        self.assertEqual(r["tasks"][0]["roi"]["status"], "unavailable")

    def test_roi_scenario(self):
        r = analyze(data(tasks=[task()]), prices())
        self.assertEqual(r["tasks"][0]["roi"]["status"], "scenario_estimate")
        self.assertEqual(r["tasks"][0]["roi"]["net_savings"], "44.997")

    def test_roi_verified_basis(self):
        r = analyze(data([sample(amount="1", origin="actual", currency="USD")], [task()]))
        self.assertEqual(r["tasks"][0]["roi"]["status"], "verified_basis")

    def test_roi_unknown_or_mixed_currency(self):
        r = analyze(data(tasks=[task(currency="CNY")]), prices())
        self.assertEqual(r["tasks"][0]["roi"]["status"], "unavailable")

    def test_no_double_human(self):
        r = analyze(data([sample(kind="human", amount="2", origin="manual", currency="USD")], [task()]))
        self.assertEqual(r["totals"]["USD"]["manual"], "2")
        self.assertEqual(r["tasks"][0]["roi"]["status"], "unavailable")

    def test_overlap_rejected(self):
        p = prices().prices[0]
        with self.assertRaises(ValueError):
            PriceBook({"schema_version": "1.0", "prices": [p, dict(p, id="other")]})

    def test_invalid_numbers(self):
        for val in ("NaN", "Infinity", "-1", True):
            with self.subTest(val=val), self.assertRaises(ValueError):
                money(val)
        with self.assertRaises(ValueError):
            sample(cached_tokens=1001)
        with self.assertRaises(ValueError):
            sample(input_tokens=1.5)


class Waste(unittest.TestCase):
    def calls(self, **kwargs):
        return [sample(id=f"e{i}", kind="tool", action="shell", signature="SYNTHETIC-command", status="failed", **kwargs) for i in range(3)]

    def test_repeated_failures_evidence(self):
        f = detect(self.calls())
        self.assertEqual(f[0]["rule"], "repeated_failure")
        self.assertEqual([e["event_id"] for e in f[0]["evidence"]], ["e0", "e1", "e2"])

    def test_reasonable_retries(self):
        for reason in ("transient", "user_requested", "idempotent_check"):
            self.assertEqual(detect(self.calls(retry_reason=reason)), [])

    def test_progress_exempt(self):
        self.assertEqual(detect(self.calls(progress=True)), [])

    def test_single_duplicate_insufficient(self):
        self.assertEqual(detect(self.calls()[:2]), [])

    def test_cross_task_separation(self):
        calls = self.calls()
        for i, e in enumerate(calls):
            e["task_id"] = str(i)
        self.assertEqual(detect(calls), [])

    def test_loop(self):
        calls = [sample(id=str(i), kind="tool", signature=str(i % 2)) for i in range(6)]
        self.assertIn("alternating_loop", [f["rule"] for f in detect(calls)])

    def test_read_and_edit(self):
        for action, rule in (("read_file", "repeated_read"), ("edit_file", "unverified_rework")):
            calls = self.calls(progress=False)
            for e in calls:
                e.update(action=action, status="success")
            self.assertEqual(detect(calls)[0]["rule"], rule)

    def test_post_failure_and_context(self):
        evs = [sample(id="end", kind="task", status="failed")]
        evs += [sample(id=str(i), input_tokens=20000, context_signature="SYNTHETIC-context", amount="2", origin="actual", currency="USD", progress=False) for i in range(3)]
        rules = {f["rule"] for f in detect(evs)}
        self.assertTrue({"cost_after_failure", "context_reload", "cost_without_progress"} <= rules)


class Imports(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def save(self, rows, name="input.jsonl"):
        p = self.root / name
        p.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
        return p

    def test_jsonl_csv_unicode_paths(self):
        p = self.save([sample()], "合成 Windows path.jsonl")
        a = import_file(p)
        p = self.root / "SYNTHETIC.csv"
        with p.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=list(sample()))
            writer.writeheader()
            row = sample()
            row["synthetic"] = "true"
            writer.writerow(row)
        b = import_file(p, "csv")
        self.assertEqual(a["events"][0]["input_tokens"], b["events"][0]["input_tokens"])

    def test_empty_and_malformed(self):
        p = self.save([])
        self.assertEqual(import_file(p)["warnings"], ["EMPTY_INPUT"])
        for text in ("{", "[]", "null"):
            p.write_text(text)
            with self.assertRaises(ValueError):
                import_file(p)

    def test_schema_incompatible(self):
        p = self.save([dict(sample(), schema_version="99")])
        with self.assertRaises(ValueError):
            import_file(p)

    def test_secrets_discarded(self):
        raw = dict(sample(), prompt="password=SUPER_PRIVATE", cookie="SESSID_PRIVATE", arguments={"api_key": "sk-SYNTHETIC-secret"})
        raw["action"] = "password=SECRET"
        out = json.dumps(import_file(self.save([raw])))
        for secret in ("SUPER_PRIVATE", "SESSID_PRIVATE", "sk-SYNTHETIC-secret", "password=SECRET"):
            self.assertNotIn(secret, out)
        self.assertNotIn("arguments", out)

    def test_no_execution_or_modification(self):
        marker = self.root / "must-not-exist"
        p = self.save([dict(sample(), arguments={"command": f"touch {marker}"})])
        before = p.read_bytes()
        import_file(p)
        self.assertEqual(p.read_bytes(), before)
        self.assertFalse(marker.exists())

    def test_doctor_read_only(self):
        p = self.save([sample()])
        before = p.read_bytes()
        self.assertTrue(check(p)["ok"])
        self.assertEqual(before, p.read_bytes())
        self.assertFalse(check(self.root / "missing")["ok"])

    def test_duplicate_ids(self):
        with self.assertRaises(ValueError):
            import_file(self.save([sample(), sample()]))

    def test_codex_cumulative_not_repeated_last(self):
        rows = [(1, {"type": "session_meta", "payload": {"id": "SYNTHETIC", "cli_version": "0.142.0"}}),
                (2, {"type": "turn_context", "payload": {"model": "SYNTHETIC-model"}})]
        for i, count in enumerate((100, 100, 200), 3):
            rows.append((i, {"type": "event_msg", "timestamp": "2026-10-01T00:00:00Z", "payload": {"type": "token_count", "info": {"total_token_usage": {"input_tokens": count, "output_tokens": count // 10, "cached_input_tokens": 0}}}}))
        events, _, _ = codex.convert(rows)
        self.assertEqual(sum(e["input_tokens"] for e in events), 200)
        self.assertEqual(len(events), 2)
        rows[0][1]["payload"]["cli_version"] = "99.0"
        with self.assertRaises(ValueError):
            codex.convert(rows)

    def test_claude_dedup_cache_inclusive(self):
        row = {"type": "assistant", "sessionId": "SYNTHETIC", "version": "2.0.0", "timestamp": "2026-10-01T00:00:00Z", "message": {"id": "msg1", "model": "SYNTHETIC-model", "usage": {"input_tokens": 10, "output_tokens": 2, "cache_read_input_tokens": 50, "cache_creation_input_tokens": 20}, "content": []}}
        evs, _, _ = claude.convert([(1, row), (2, copy.deepcopy(row))])
        self.assertEqual(len(evs), 1)
        self.assertEqual(evs[0]["input_tokens"], 80)
        row["version"] = "99.0"
        with self.assertRaises(ValueError):
            claude.convert([(1, row)])

    def test_openai_and_reject_stream(self):
        row = {"object": "response", "id": "SYNTHETIC-resp", "created_at": 1790812800, "status": "completed", "model": "SYNTHETIC-model", "usage": {"input_tokens": 10, "output_tokens": 2, "input_tokens_details": {"cached_tokens": 4}}}
        evs, _, _ = openai.convert([(1, row)])
        self.assertEqual(evs[0]["cached_tokens"], 4)
        row["object"] = "response.output_text.delta"
        with self.assertRaises(ValueError):
            openai.convert([(1, row)])

    def test_errors_never_echo_secrets(self):
        p = self.save([dict(sample(), input_tokens="sk-SYNTHETIC-secret")])
        stream = io.StringIO()
        with redirect_stderr(stream):
            code = main(["import", str(p), "-o", str(self.root / "out.json")])
        self.assertEqual(code, 2)
        self.assertNotIn("SYNTHETIC-secret", stream.getvalue())


class ReportsAndCLI(unittest.TestCase):
    def test_schema_validation(self):
        r = analyze(data(tasks=[task()]), prices())
        schema = json.loads((ROOT / "schemas" / "audit.schema.json").read_text())
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.validate(r, schema)
        bad = copy.deepcopy(r)
        bad["charges"][0]["origin"] = "invented"
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(bad, schema)

    def test_html_escaped_offline(self):
        r = analyze(data([sample(id="<script>alert(1)</script>")]), prices())
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "r.html"
            write(r, p, "html")
            html = p.read_text(encoding="utf-8")
            self.assertNotIn("<script>", html)
            self.assertIn("&lt;script&gt;", html)
            self.assertIn("Content-Security-Policy", html)
            self.assertNotIn('<script src=', html)

    def test_csv_formula_guard(self):
        r = analyze(data([sample(id="=DANGER", task_id="@BAD")]), prices())
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "r.csv"
            write(r, p, "csv")
            self.assertIn("'=DANGER", p.read_text())

    def test_comparison_same_task_only(self):
        a = analyze(data(tasks=[task()]), prices())
        b = analyze(data([sample(id="e2", task_id="t2", agent="claude-code")], [task(task_id="t2", agent="claude-code")]), prices())
        c = compare([a, b])
        self.assertEqual(len(c["groups"]), 1)
        self.assertTrue(c["groups"][0]["comparable"])
        b["tasks"][0]["acceptance_id"] = "different"
        self.assertEqual(len(compare([a, b])["groups"]), 2)

    def test_comparison_incomplete_separated(self):
        a = analyze(data(tasks=[task()]), prices())
        b = analyze(data([sample(id="e2", task_id="t2", agent="claude-code", model="unknown")], [task(task_id="t2", agent="claude-code")]), prices())
        self.assertEqual(len(compare([a, b])["groups"]), 2)

    def test_cli_all_help(self):
        for command in ("import", "analyze", "compare", "report", "pricing", "doctor"):
            p = subprocess.run([sys.executable, "-m", "agentwaste", command, "--help"], capture_output=True)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertIn(b"usage:", p.stdout)

    def test_cli_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            source, canonical, report = (tmp / s for s in ("raw.jsonl", "data.json", "audit.json"))
            source.write_text(json.dumps(sample()))
            commands = [["import", str(source), "-o", str(canonical)], ["analyze", str(canonical), "-o", str(report)],
                        ["compare", str(canonical), "-o", str(tmp / "compare.json")], ["report", str(report), "-o", str(tmp / "report.html")],
                        ["pricing"], ["doctor", "--input", str(source)]]
            for cmd in commands:
                p = subprocess.run([sys.executable, "-m", "agentwaste", *cmd], capture_output=True, text=True)
                self.assertEqual(p.returncode, 0, p.stderr)
            self.assertTrue((tmp / "report.html").exists())

    def test_output_cannot_overwrite_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "raw.jsonl"
            p.write_text(json.dumps(sample()))
            before = p.read_bytes()
            with redirect_stderr(io.StringIO()):
                self.assertEqual(main(["import", str(p), "-o", str(p)]), 2)
            self.assertEqual(before, p.read_bytes())

    def test_task_validation(self):
        with self.assertRaises(ValueError):
            tasks_validate([task(accepted="false")])
        with self.assertRaises(ValueError):
            tasks_validate([task(), task()])

    def test_comparison_dimensions(self):
        a = analyze(data(tasks=[task(prompt_strategy="short", workflow="single")]), prices())
        b = analyze(data([sample(id="e2", task_id="t2", model="different")], [task(task_id="t2", prompt_strategy="long", workflow="parallel")]), prices(model="different"))
        for dimension in ("model", "prompt_strategy", "workflow"):
            c = compare([a, b], by=dimension)
            self.assertEqual(len(c["groups"][0]["agents"]), 2)
            self.assertTrue(c["synthetic"])

    def test_task_without_events_no_roi(self):
        r = analyze(data([], [task()]), prices())
        self.assertEqual(r["tasks"][0]["roi"]["status"], "unavailable")
        self.assertIsNone(r["average_cost_per_success"])

    def test_validate_all_demo_schemas(self):
        from agentwaste.importers.base import import_file
        schema = json.loads((ROOT / "schemas" / "event.schema.json").read_text())
        for name, format in (("success", "jsonl"), ("waste", "jsonl"), ("codex-native", "codex"), ("claude-native", "claude"), ("openai-native", "openai")):
            d = import_file(ROOT / "examples" / f"{name}.jsonl", format)
            for e in d["events"]:
                jsonschema.validate(e, schema)

    def test_native_multi_session_rejected(self):
        with self.assertRaises(ValueError):
            codex.convert([(1, {"type": "session_meta", "payload": {"id": "a"}}), (2, {"type": "session_meta", "payload": {"id": "b"}})])
        with self.assertRaises(ValueError):
            claude.convert([(1, {"sessionId": "a"}), (2, {"sessionId": "b"})])

    def test_count_and_currency_fields_not_free_text(self):
        for kw in ({"source_line": "SECRET"}, {"currency": "SECRET"}, {"origin": "SECRET"}):
            with self.subTest(kw=kw), self.assertRaises(ValueError):
                sample(**kw)

    def test_hardlink_source_preserved(self):
        import os
        with tempfile.TemporaryDirectory() as tmp:
            source, output = Path(tmp) / "source.jsonl", Path(tmp) / "hardlink.json"
            source.write_text(json.dumps(sample()))
            os.link(source, output)
            before = source.read_bytes()
            with redirect_stderr(io.StringIO()):
                self.assertEqual(main(["import", str(source), "-o", str(output)]), 2)
            self.assertEqual(before, source.read_bytes())

    def test_claude_partial_cache_is_unknown(self):
        row = {"type": "assistant", "version": "2.0", "sessionId": "SYNTHETIC", "timestamp": "2026-10-01T00:00:00Z", "message": {"id": "msg", "model": "SYNTHETIC-model", "usage": {"input_tokens": 100, "output_tokens": 10, "cache_read_input_tokens": 0}}}
        evs, warnings, _ = claude.convert([(1, row)])
        self.assertIn("TOKEN_USAGE_INCOMPLETE", warnings)
        self.assertEqual(prices().estimate(evs[0])[1], "TOKEN_USAGE_INCOMPLETE")

    def test_privacy_task_id_collision_rejected(self):
        with self.assertRaises(ValueError):
            tasks_validate([task(task_id="sk-SYNTHETIC-one"), task(task_id="sk-SYNTHETIC-two")])

    def test_missing_hourly_rate_retains_unknown(self):
        t = task()
        del t["hourly_rate"]
        r = analyze(data(tasks=[t]), prices())
        self.assertEqual(r["coverage"]["unknown_cost_items"], 1)
        self.assertEqual(r["tasks"][0]["roi"]["status"], "unavailable")

    def test_zero_cost_roi_undefined(self):
        r = analyze(data([sample(amount="0", origin="actual", currency="USD")], [task(human_minutes="0", rework_minutes="0")]))
        self.assertIsNone(r["tasks"][0]["roi"]["roi"])

    def test_report_schema_for_all_generated_audits(self):
        audit_schema = json.loads((ROOT / "schemas" / "audit.schema.json").read_text())
        ds_schema = json.loads((ROOT / "schemas" / "dataset.schema.json").read_text())
        reports = []
        for name in ("success", "waste", "claude"):
            d = import_file(ROOT / "examples" / f"{name}.jsonl")
            d["tasks"] = tasks_validate(json.loads((ROOT / "examples" / f"{name}.tasks.json").read_text()))
            jsonschema.validate(d, ds_schema)
            r = analyze(d, prices())
            jsonschema.validate(r, audit_schema)
            reports.append(r)
        jsonschema.validate(compare([reports[0], reports[2]]), json.loads((ROOT / "schemas" / "comparison.schema.json").read_text()))


if __name__ == "__main__":
    unittest.main()
