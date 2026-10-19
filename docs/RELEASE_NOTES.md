# AgentWaste v0.1.0

Find the Hidden Cost of AI Work.

Offline task economics auditing for AI agents, with an MIT-licensed Python CLI and Agent Skill. No runtime third-party dependencies, telemetry, paid API or automatic private-directory scanning.

- Six commands: import, analyze, compare, report, pricing and read-only doctor.
- Generic JSONL/CSV; experimental Codex/Claude Code structural profiles; completed OpenAI API objects.
- Decimal accounting with original currencies, dated prices and separate reported, estimated, manual and unknown costs. Caller Decimal settings cannot silently reduce financial precision.
- Reviewable failure/retry/read/edit/loop/context/post-failure findings, configurable repetition windows and original-currency thresholds, progress and justified-check exemptions.
- Acceptance-gated ROI, and task/difficulty/acceptance/coverage-grouped comparisons with normalized per-attempt/per-success costs, known-outcome denominators and median observed durations.
- Strict runtime and exported event/task/pricing/dataset/audit/comparison schemas; duplicate-key, malformed CSV and bounded-input checks. Atomic report replacement preserves existing files on write failure.
- JSON/CSV/Markdown/self-contained HTML with summaries, evidence, timelines, high-cost steps and UTC trends. Comparison CSV includes actual metrics.
- Reproducible SYNTHETIC demos and regression tests, wheel smoke validation outside the checkout, and a 12-environment GitHub Actions matrix.

All bundled examples and rates are SYNTHETIC, not real provider prices or a Codex/Claude benchmark. Native profiles are experimental and tested with synthetic layouts; no universal native version compatibility, subscription invoice allocation, automatic human-effort inference or FX conversion is claimed. Findings require review, and ROI is not independent billing certification or guaranteed savings.

See `docs/validation.md` and the release's validation assets for checks actually executed. A public Release must follow a successful CI run for the exact published commit; no unexecuted platform job is claimed as passed.
