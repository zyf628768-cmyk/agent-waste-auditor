"""Regression cases discovered during the pre-release review. All data SYNTHETIC."""
import copy
from decimal import localcontext, Decimal, Inexact, ROUND_UP
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from contextlib import redirect_stderr

import jsonschema
from test_audit import sample, prices, task, data, ROOT
from agentwaste.safeio import parse_json, InputError
from agentwaste.models import event, money, tasks_validate, fingerprint
from agentwaste.importers.base import import_file, load, dataset
from agentwaste.importers import claude, codex
from agentwaste.costs import analyze
from agentwaste.compare import compare
from agentwaste.reports import write
from agentwaste.schemas import SCHEMAS, validate, validate_report
from agentwaste.pricing import PriceBook
from agentwaste.cli import main
from agentwaste.rules import Rules
from agentwaste.waste import detect


class InputBoundaries(unittest.TestCase):
    def test_duplicate_json_keys(self):
        with self.assertRaises(InputError) as result:
            parse_json('{"amount":"1", "amount":"2"}', 7)
        self.assertEqual(result.exception.code, "DUPLICATE_JSON_KEY")
        self.assertEqual(result.exception.line, 7)

    def test_nonfinite_json(self):
        for value in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(value=value), self.assertRaises(InputError):
                parse_json('{"x":' + value + '}')

    def test_nesting_bound(self):
        with self.assertRaises(InputError):
            parse_json('[' * 50 + '0' + ']' * 50)

    def test_malformed_csv_not_silently_accepted(self):
        for text in ('id,id\na,b\n', 'id,task_id\na,b,c\n', 'id,task_id\na\n', 'id,task_id\n"open,b\n'):
            with self.subTest(text=text), tempfile.TemporaryDirectory() as tmp:
                p = Path(tmp) / "SYNTHETIC.csv"
                p.write_text(text)
                with self.assertRaises(InputError):
                    import_file(p, "csv")

    def test_untrusted_warning_dropped(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "SYNTHETIC.json"
            p.write_text(json.dumps(dict(data(), warnings=["SUPERPRIVATE", "EMPTY_INPUT"])))
            self.assertEqual(dataset(p)["warnings"], ["EMPTY_INPUT"])

    def test_non_utf8_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "SYNTHETIC.jsonl"
            p.write_bytes(b'\xff\xff')
            stream = io.StringIO()
            with redirect_stderr(stream):
                self.assertEqual(main(["import", str(p), "-o", str(Path(tmp) / "out")]), 2)
            self.assertIn("INPUT_NOT_UTF8", stream.getvalue())

    def test_safe_error_location(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "SYNTHETIC.jsonl"
            p.write_text('\n{SUPERPRIVATE')
            stream = io.StringIO()
            with redirect_stderr(stream):
                self.assertEqual(main(["import", str(p), "-o", str(Path(tmp) / "out")]), 2)
            self.assertIn("source line 2", stream.getvalue())
            self.assertNotIn("SUPERPRIVATE", stream.getvalue())

    def test_label_types_and_limits(self):
        for val in ([], {}, 7, " ", "x" * 161, "line\nprivate"):
            with self.subTest(value=val), self.assertRaises(ValueError):
                sample(agent=val)

    def test_no_truncation_collision(self):
        with self.assertRaises(ValueError):
            sample(id="x" * 161)

    def test_task_labels_not_mistaken_for_secret_tokens(self):
        self.assertEqual(sample(task_id="SYNTHETIC-task-12")["task_id"], "SYNTHETIC-task-12")

    def test_generic_task_identity_collision_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "SYNTHETIC.jsonl"
            p.write_text('\n'.join(json.dumps(dict(sample(id=str(i)), task_id=secret)) for i, secret in enumerate(("sk-SYNTHETIC-one", "sk-SYNTHETIC-two"))))
            with self.assertRaises(InputError):
                import_file(p)

    def test_named_secret_values_redacted_before_hashing(self):
        self.assertEqual(fingerprint({"password": "SYNTHETIC-one"}), fingerprint({"password": "SYNTHETIC-two"}))
        self.assertNotEqual(fingerprint({"path": "SYNTHETIC-task-one"}), fingerprint({"path": "SYNTHETIC-task-two"}))

    def test_accepted_status_contradiction(self):
        with self.assertRaises(ValueError):
            tasks_validate([task(status="failed", accepted=True)])

    def test_partial_cache_preserved_as_unknown(self):
        e = event({k: v for k, v in sample(cached_tokens=40).items() if k != "input_tokens"})
        self.assertEqual(e["cached_tokens"], 40)
        self.assertEqual(prices().estimate(e)[1], "TOKEN_USAGE_INCOMPLETE")

    def test_marker_charge_needs_category(self):
        with self.assertRaises(ValueError):
            sample(kind="task", amount="1", origin="manual", currency="USD")
        r = analyze(data([sample(kind="task", amount="1", origin="manual", currency="USD", category="quality")]))
        validate_report(r)

    def test_unicode_line_separator_inside_json_string(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "SYNTHETIC.jsonl"
            p.write_text(json.dumps(dict(sample(), arguments="SYNTHETIC\u2028value"), ensure_ascii=False), encoding="utf-8")
            self.assertEqual(len(import_file(p)["events"]), 1)

    def test_human_event_category(self):
        r = analyze(data([sample(kind="human", category="human", amount="1", origin="manual", currency="USD")]))
        validate_report(r)


class FinancialBoundaries(unittest.TestCase):
    def test_caller_decimal_context_does_not_change_cost(self):
        with localcontext() as context:
            context.prec = 2
            r = analyze(data(tasks=[task(human_minutes="1", rework_minutes="1", hourly_rate="1")]), prices())
        self.assertEqual(r["totals"]["USD"]["estimated"], "0.003")
        self.assertGreater(len(r["totals"]["USD"]["manual"]), 30)
        validate_report(r)

    def test_repeating_human_fraction_not_rejected(self):
        r = analyze(data(tasks=[task(human_minutes="1", rework_minutes="0", hourly_rate="1")]), prices())
        self.assertEqual(r["tasks"][0]["roi"]["status"], "scenario_estimate")

    def test_caller_rounding_and_traps_do_not_change_audit(self):
        baseline = analyze(data(tasks=[task(human_minutes="1", rework_minutes="0", hourly_rate="1")]), prices())
        with localcontext() as context:
            context.rounding = ROUND_UP
            context.traps[Inexact] = True
            observed = analyze(data(tasks=[task(human_minutes="1", rework_minutes="0", hourly_rate="1")]), prices())
        self.assertEqual(observed, baseline)

    def test_unbounded_exponents_rejected(self):
        for value in ("1e100000", "1e-100000", "9" * 500):
            with self.subTest(value=value), self.assertRaises(ValueError):
                money(value)

    def test_utc_price_date(self):
        book = prices(effective_from="2026-10-02", effective_to="2026-10-02")
        self.assertIsNone(book.estimate(sample(timestamp="2026-10-01T23:00:00-02:00"))[1])

    def test_noncanonical_price_dates_rejected(self):
        with self.assertRaises(ValueError):
            prices(effective_from="20260101")

    def test_empty_price_object_not_silently_defaulted(self):
        with self.assertRaises(ValueError):
            PriceBook({})

    def test_precise_elapsed_microseconds(self):
        r = analyze(data([sample(id="a", timestamp="1900-01-01T00:00:00.000001Z"), sample(id="b", timestamp="2026-10-01T00:00:00.000002Z")]), prices())
        self.assertTrue(r["tasks"][0]["elapsed_seconds"].endswith(".000001"))

    def test_model_metadata_cannot_override_evidence(self):
        with self.assertRaises(ValueError):
            analyze(data(tasks=[task(model="wrong-model")]), prices())

    def test_coverage_counts_explicit_wait_charge(self):
        r = analyze(data([sample(kind="wait", amount="1", origin="manual", currency="USD")]))
        self.assertEqual(r["tasks"][0]["cost_coverage"]["known_events"], 1)
        self.assertEqual(r["tasks"][0]["cost_coverage"]["cost_bearing_events"], 1)

    def test_zero_estimated_cost_still_scenario(self):
        r = analyze(data([sample(amount="0", origin="estimated", currency="USD")], [task()]))
        self.assertEqual(r["tasks"][0]["roi"]["status"], "scenario_estimate")

    def test_missing_model_not_inferred_from_other_calls(self):
        unknown = sample(id="e2")
        del unknown["model"]
        r = analyze(data([sample(), unknown]), prices())
        self.assertIsNone(r["tasks"][0]["model"])


class NativeBoundaries(unittest.TestCase):
    def assistant(self, usage):
        return {"type": "assistant", "sessionId": "SYNTHETIC", "version": "2.0", "timestamp": "2026-10-01T00:00:00Z", "message": {"id": "SYNTHETIC-msg", "model": "SYNTHETIC-model", "usage": usage, "content": []}}

    def test_claude_missing_usage_not_omitted(self):
        evs, _, _ = claude.convert([(1, self.assistant(None))])
        self.assertEqual(len(evs), 1)
        self.assertEqual(prices().estimate(evs[0])[1], "TOKEN_USAGE_INCOMPLETE")

    def test_claude_positive_partial_cache_downgrades(self):
        evs, _, _ = claude.convert([(1, self.assistant({"input_tokens": 10, "output_tokens": 2, "cache_read_input_tokens": 100}))])
        self.assertEqual(len(evs), 1)
        self.assertEqual(prices().estimate(evs[0])[1], "TOKEN_USAGE_INCOMPLETE")

    def test_claude_conflicting_request_usage_rejected(self):
        first = self.assistant({"input_tokens": 10, "output_tokens": 2, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0})
        second = copy.deepcopy(first)
        second["message"]["usage"]["input_tokens"] = 11
        with self.assertRaises(ValueError):
            claude.convert([(1, first), (2, second)])

    def test_claude_regressing_output_rejected(self):
        first = self.assistant({"input_tokens": 10, "output_tokens": 2, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0})
        second = copy.deepcopy(first)
        second["message"]["usage"]["output_tokens"] = 1
        with self.assertRaises(ValueError):
            claude.convert([(1, first), (2, second)])

    def test_claude_invalid_counts_rejected(self):
        with self.assertRaises(ValueError):
            claude.convert([(1, self.assistant({"input_tokens": True}))])

    def test_codex_gap_preserves_unknown_cost_event(self):
        rows = [(1, {"type": "session_meta", "payload": {"id": "SYNTHETIC", "cli_version": "0.142"}}),
                (2, {"type": "turn_context", "payload": {"model": "SYNTHETIC-model"}}),
                (3, {"timestamp": "2026-10-01T00:00:00Z", "type": "event_msg", "payload": {"type": "token_count", "info": None}})]
        evs, warnings, _ = codex.convert(rows)
        self.assertEqual(len(evs), 1)
        self.assertFalse(evs[0]["usage_complete"])
        self.assertIn("CUMULATIVE_USAGE_UNAVAILABLE", warnings)


class ComparisonAndReports(unittest.TestCase):
    def test_unequal_attempts_have_normalized_costs(self):
        reports = []
        for i, agent in enumerate(("codex", "codex", "claude-code")):
            reports.append(analyze(data([sample(id=str(i), task_id=str(i), agent=agent)], [task(task_id=str(i), agent=agent)]), prices()))
        r = compare(reports)
        a, b = r["groups"][0]["agents"]
        self.assertNotEqual(a["totals"], b["totals"])
        self.assertEqual(a["cost_per_attempt"], b["cost_per_attempt"])
        validate_report(r)

    def test_monetary_basis_groups_separate(self):
        a = analyze(data(tasks=[task()]), prices())
        b = analyze(data([sample(id="e2", task_id="t2", amount="1", origin="actual", currency="USD")], [task(task_id="t2")]), prices())
        self.assertEqual(len(compare([a, b])["groups"]), 2)

    def test_human_coverage_groups_separate(self):
        a = analyze(data(tasks=[task()]), prices())
        other = task(task_id="t2")
        del other["human_minutes"]
        b = analyze(data([sample(id="e2", task_id="t2")], [other]), prices())
        self.assertEqual(len(compare([a, b])["groups"]), 2)

    def test_explicit_failed_status_is_known_without_acceptance(self):
        t = task(status="failed", accepted=None)
        r = compare([analyze(data(tasks=[t]), prices())])
        self.assertEqual(r["groups"][0]["agents"][0]["known_outcomes"], 1)
        self.assertEqual(r["groups"][0]["agents"][0]["success_rate"], "0")

    def test_runtime_and_external_schema_agree(self):
        for kind, r in (("audit", analyze(data(tasks=[task()]), prices())), ("comparison", compare([analyze(data(tasks=[task()]), prices())]))):
            validate(r, SCHEMAS[kind])
            jsonschema.validate(r, SCHEMAS[kind])
            malformed = copy.deepcopy(r)
            malformed["PRIVATE_RAW_PROMPT"] = "SUPERPRIVATE"
            with self.assertRaises(InputError):
                validate_report(malformed)
            with self.assertRaises(jsonschema.ValidationError):
                jsonschema.validate(malformed, SCHEMAS[kind])

    def test_forged_report_totals_rejected(self):
        r = analyze(data(), prices())
        r["totals"]["USD"]["estimated"] = "999"
        with self.assertRaises(InputError):
            validate_report(r)

    def test_roi_label_requires_its_economic_evidence(self):
        r = analyze(data(tasks=[task()]), prices())
        r["tasks"][0]["roi"] = {"status": "verified_basis"}
        with self.assertRaises(InputError):
            validate_report(r)

    def test_cross_task_charge_attribution_rejected(self):
        r = analyze(data([sample(), sample(id="second", task_id="t2")]), prices())
        r["charges"][0]["task_id"] = "t2"
        with self.assertRaises(InputError):
            validate_report(r)

    def test_comparison_outcome_counts_consistent(self):
        r = compare([analyze(data(tasks=[task()]), prices())])
        r["groups"][0]["agents"][0]["successes"] = 2
        with self.assertRaises(InputError):
            validate_report(r)

    def test_atomic_failure_preserves_existing_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "report.json"
            p.write_text("ORIGINAL")
            with patch("agentwaste.safeio.os.replace", side_effect=OSError("SYNTHETIC disk error")):
                with self.assertRaises(OSError):
                    write(analyze(data(), prices()), p)
            self.assertEqual(p.read_text(), "ORIGINAL")
            self.assertEqual(list(Path(tmp).glob(".agentwaste-*")), [])

    def test_comparison_csv_contains_metrics(self):
        r = compare([analyze(data(tasks=[task()]), prices())])
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "comparison.csv"
            write(r, p, "csv")
            text = p.read_text()
            self.assertIn("per_attempt", text)
            self.assertIn("codex", text)

    def test_markdown_labels_cannot_embed_remote_images(self):
        from agentwaste.reports import markdown_summary
        r = analyze(data([sample(id="![SYNTHETIC](https://example.invalid/image)")]), prices())
        # Task identifiers are the Markdown table's user-supplied labels.
        r["tasks"][0]["task_id"] = "![SYNTHETIC](https://example.invalid/image)"
        summary = markdown_summary(r)
        self.assertIn('\\!\\[SYNTHETIC\\]', summary)


class HeuristicBoundaries(unittest.TestCase):
    def calls(self):
        return [sample(id=str(i), kind="tool", action="read_file", signature="SYNTHETIC-file", timestamp=f"2026-10-01T00:00:0{i}Z") for i in range(3)]

    def test_progress_interrupts_repetition(self):
        evs = self.calls()
        evs.insert(1, sample(id="progress", kind="task", progress=True, timestamp="2026-10-01T00:00:00.5Z"))
        self.assertEqual(detect(evs), [])

    def test_time_window_prevents_remote_repeats(self):
        evs = self.calls()
        evs[-1]["timestamp"] = "2026-10-02T00:00:00Z"
        self.assertEqual(detect(evs), [])

    def test_custom_threshold(self):
        self.assertEqual(detect(self.calls(), Rules(repetition_threshold=4)), [])
        self.assertTrue(detect(self.calls()))

    def test_unconfigured_currency_not_called_expensive(self):
        evs = [sample(kind="tool", amount="10", origin="actual", currency="JPY", progress=False)]
        self.assertEqual(detect(evs), [])
        self.assertEqual(detect(evs, Rules(high_cost_thresholds={"JPY": "5"}))[0]["rule"], "cost_without_progress")

    def test_invalid_rules(self):
        for extra in ({"repetition_threshold": 2}, {"window_seconds": True}, {"high_cost_thresholds": {"USD": "NaN"}}, {"unknown": 3}):
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                Rules.from_dict({"schema_version": "1.0", **extra})

    def test_loop_threshold_applies_to_cycle_count(self):
        evs = [sample(id=str(i), kind="tool", signature=str(i % 2)) for i in range(6)]
        self.assertIn('alternating_loop', {f['rule'] for f in detect(evs)})
        self.assertNotIn('alternating_loop', {f['rule'] for f in detect(evs, Rules(repetition_threshold=4))})

    def test_unknown_task_marker_does_not_reopen_failure(self):
        evs = [sample(id='failed', kind='task', status='failed'), sample(id='unknown', kind='task'), sample(id='charged', amount='1', origin='actual', currency='USD')]
        self.assertIn('cost_after_failure', {f['rule'] for f in detect(evs)})

    def test_explicit_reopen_clears_failure(self):
        evs = [sample(id='failed', kind='task', status='failed'), sample(id='reopened', kind='task', status='running'), sample(id='charged', amount='1', origin='actual', currency='USD')]
        self.assertEqual(detect(evs), [])

    def test_zero_charge_after_failure_is_not_spend(self):
        evs = [sample(id='failed', kind='task', status='failed'), sample(id='free', amount='0', origin='actual', currency='USD')]
        self.assertEqual(detect(evs), [])


if __name__ == "__main__":
    unittest.main()
