# AgentWaste

**Find the Hidden Cost of AI Work.**

An MIT-licensed, local-first CLI and Agent Skill for auditing AI task economics: model/tool charges, failed attempts, rework, human involvement, waiting and acceptance. Python 3.11+, Windows/Linux/macOS. No runtime dependencies, paid API, telemetry, log upload or automatic private-directory discovery.

**v0.1.0 is an evidence-preserving MVP.** Findings are suspicions for human review, not proof of waste. Unknown cost never becomes zero. Native Codex/Claude adapters are experimental structural profiles, tested with SYNTHETIC fixtures; no claim of universal log compatibility or billing reconciliation.

Pre-release review added stricter schemas and parsing, atomic output, configurable detection windows, normalized comparison metrics, installed-wheel validation, and a publication script that gates a Release on all 12 CI jobs for the exact source commit. Local test and benchmark evidence are linked in [validation](docs/validation.md).

## Install and run

From this source directory:

```sh
python -m pip install .
agentwaste --help
agentwaste import examples/success.jsonl --tasks examples/success.tasks.json -o events.json
agentwaste analyze events.json --pricing examples/pricing.json -o audit.json
agentwaste report audit.json --format html -o audit.html
agentwaste report audit.json --format markdown -o audit.md
agentwaste report audit.json --format csv -o audit.csv
agentwaste pricing examples/pricing.json
agentwaste doctor --input examples/success.jsonl --pricing examples/pricing.json
python scripts/demo.py
```

`python -m agentwaste` also works from the source checkout. All six commands have `--help`. `import --format` accepts `jsonl`, `csv`, `codex`, `claude`, `openai`. Import exactly one explicitly named file at a time. Originals are read-only, and the CLI rejects outputs that resolve to any supplied input. Existing output files may be replaced. Do not put reports into private source-log paths.

## What is counted

Costs are decimal strings and remain separated into `actual` (a charge reported by the input, not independently verified), `estimated` (dated price × known tokens) and `manual` (user-entered charges/effort). Missing prices, expired prices, partial usage and unpriced tools appear as unknown cost items. Totals are observed subtotals, never a claim to include unlogged services or labor. Currencies are retained without FX conversion.

Canonical input tokens **include cache reads and cache writes**. The formula is `(input-read-write) × input_rate + read × read_rate + write × write_rate + output × output_rate`, divided by one million. Cache-read count must be explicitly present for estimation; cache-write defaults to zero in the canonical format. Cache-write price must be supplied when writes occur. Native Claude input excludes cached tokens, so its adapter adds them. Use separate model/rate IDs for cache TTLs or tiers; ambiguous cache-write pricing is unknown. No commercial prices are bundled. The example model and prices are **SYNTHETIC**, not current provider pricing.

Failures retain their charges. `failed_step_costs` is an overlapping attribution view, not an additional charge to add to totals. An event may have one cost category: model, tool, failure handling, rework, waiting or quality handling. Task-level human cost is another component. Rework minutes exclude other human minutes. Human event charges and task-level human estimates require reconciliation, avoiding double counting. Waiting, queue time and wall time are reported without automatic wage conversion. Elapsed time is the envelope of observed timestamps, not complete task runtime; overlapping durations are shown as a separate sum.

ROI requires an accepted successful task, baseline, hourly rate, complete human and rework minutes, and no unknown charges or currency mismatch. It is a `scenario_estimate` when prices are estimates or the human baseline is unverified; `verified_basis` means a user-declared verified baseline and reported/manual charges, **not an independent financial certification**. Missing evidence yields `unavailable`. ROI is `(baseline labor cost - total task cost) / total task cost`; zero total cost has undefined ROI.

## Review inefficiency with evidence

The MVP detects at least three identical failed calls, repeated reads/calls, A/B loops, repeated edits explicitly reporting no progress, repeated large context fingerprints, explicit costs without progress, and costs after a failed-task marker. Each finding links event IDs, source line numbers, statuses and digests, with advice. It does not execute commands or retain prompt/command bodies. `transient`, `user_requested`, `idempotent_check` retry reasons and explicitly verified progress exempt ordinary repetition rules. A transient reason is user/source evidence, not automatically inferred justification.

There is no automatic recoverable-waste dollar total: the same steps may appear in multiple findings, and a repetition can be necessary. See [methodology](docs/methodology.md) for thresholds and limitations.

Repetition defaults to a one-hour observation window; verified progress or justified checks break candidate sequences. Configure `analyze --rules examples/rules.json` (also supported by compare) to change repetition/context thresholds, window size and **per-currency** high-cost review thresholds. Only USD 1 is configured by default; another currency is never implicitly equated to it. Settings are included in each audit for reproducibility.

## Compare matching tasks

```sh
agentwaste compare examples/reports/success.events.json examples/reports/claude.events.json --pricing examples/pricing.json -o comparison.json
agentwaste report comparison.json --format html -o comparison.html
# Also supported: --by model, --by prompt_strategy, --by workflow
```

Groups require the same user-defined task key, difficulty and acceptance ID, and separate observed cost completeness, monetary basis, human-effort coverage, unknown-cost reasons and currencies. Missing matching metadata is excluded. Each variant reports total costs **and per-attempt/per-success costs**, accepted successes, unknown outcomes, human/rework involvement and median observed duration. This prevents unequal attempt counts from turning aggregate spend into a misleading ranking. Success rate denominator includes only known outcomes. Comparisons remain descriptive with no global ranking or causal claim. Users must ensure task keys refer to equivalent work. For model/strategy/workflow experiments supply the corresponding fields in task metadata. Mixed or partially missing model evidence cannot produce an inferred single-model label. Comparison CSV exports these metrics rather than an empty charge table.

## Existing tools and scope

Research checked 2026-10-19 against official product documentation:

| Tool | Existing overlapping capabilities | AgentWaste focus |
| --- | --- | --- |
| [Langfuse](https://langfuse.com/docs/observability/features/token-and-cost-tracking) | Ingested/inferred cost, usage breakdown, dated model definitions; [evaluation and experiments](https://langfuse.com/docs) | Explicit-file offline task economics with human rework and economic assumptions |
| [LangSmith](https://www.langchain.com/langsmith/observability) | Tracing, cost and latency; [evaluations](https://www.langchain.com/langsmith/evaluation) and [custom component charges](https://github.com/langchain-ai/docs/blob/main/src/langsmith/cost-tracking.mdx) | Local audit across selected agent logs, unknown-cost coverage, baseline-gated ROI |
| [Helicone](https://www.helicone.ai/) | Gateway, cost monitoring, traces, caching and provider routing | Post-run offline auditing without routing requests through a service |
| [OpenLIT](https://www.openlit.io/) | OpenTelemetry agent observability, evaluation, cost and GPU monitoring | Small CLI/Skill artifact, auditable repetition evidence and manually supplied human economics |

These products already address cost, quality and agent behavior and can be extended with custom metrics. AgentWaste does not claim to invent task cost analytics or replace their instrumentation, evaluation or production operations features. It combines a narrower local audit workflow and conservative economic reporting. Product capabilities may change.

## Demos and verification

All fixtures, labels, rates and example charges are **SYNTHETIC**. `python scripts/demo.py` runs all commands, writes their exit codes/stdout/stderr to [CLI evidence](examples/reports/cli-evidence.json), and produces:

1. [Successful task](examples/reports/success.html): USD 0.30 estimated model + 0.02 reported tool + 6.00 manual labor = **6.32**, no findings.
2. [High-waste task](examples/reports/waste.html): USD 2.42 reported + 0.1254 estimated + 27.50 manual = **30.0454**, 9 suspicions across 8 rules; failed task has unavailable ROI.
3. [Agent comparison](examples/reports/comparison.html): matching synthetic task, costs **6.32 vs 12.65**, accepted success 1/1 each, human effort 10 vs 20 minutes. This is a demonstration, not a Codex/Claude benchmark.

JSON/Markdown/HTML reports, CSV charge exports and canonical imports are in `examples/reports/`. HTML works offline with currency-separated composition/trend bars and expandable evidence, timeline, high-cost steps and coverage. No live Web Dashboard server is included.

JSON report rendering validates the full nested report shape and financial/evidence consistency locally before output. Parsing rejects duplicate JSON keys, nonfinite constants, malformed/duplicate CSV headers and inconsistent CSV row widths. Useful parser errors show safe diagnostic codes and source line numbers without source contents. Report replacement is atomic, including failure cleanup; existing reports survive a failed write. Financial arithmetic uses a local 128-digit Decimal context, independent of the calling application's precision settings; extreme numeric ranges are rejected rather than silently overflowing.

```sh
python -m pip install '.[test]' build
python -m unittest discover -s tests -v
python scripts/demo.py
python -m build
# After installing the resulting wheel outside the checkout:
python scripts/smoke_wheel.py
python scripts/benchmark.py
```

GitHub Actions defines Python 3.11–3.14 on Windows, Linux and macOS. Only the locally executed environment can be claimed as passed; see [validation](docs/validation.md) and [release checklist](docs/release.md).

## Privacy and compatibility

Prompts, message bodies, full tool arguments, tool output and source paths are discarded. Only allowlisted structured fields and redacted argument hashes are retained. Secret-like strings in labels are scrubbed, but a regex is not a general PII classifier; do not encode private text in identifiers. Stable unsalted hashes can be guessed for low-entropy inputs. Keep canonical datasets and reports private until reviewed. Reports are HTML-escaped and CSV formula prefixes are guarded. No log text is executed or treated as instructions. See [SECURITY.md](SECURITY.md).

Read [format specification](docs/formats.md) before native imports. Streaming API chunks, aggregate organization usage, undocumented native variants, reliable native tool exit extraction, subscription invoice allocation, automatic human effort inference, FX, cache TTL inference and production connectors are unsupported. Missing model labels/prices stay unavailable. `doctor` checks only named files and configuration without modification.

Project includes [SKILL.md](SKILL.md), [MIT license](LICENSE), [contribution guide](CONTRIBUTING.md), and [changelog](CHANGELOG.md).
