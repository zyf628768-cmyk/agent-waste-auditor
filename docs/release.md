# v0.1.0 release procedure

Local release assets: source ZIP, source distribution, universal Python wheel, SHA256SUMS.txt, release notes, test log and CLI evidence. ZIP includes source/docs/tests/fixtures/reports, excluding `.git`, caches, build output and private data. `scripts/package_release.py` generates deterministic source ZIP membership and integrity checks. No remote repository or public release is created automatically.

Local Git history uses the project placeholder author `AgentWaste Development <agentwaste@example.invalid>`, without changing global Git identity. Review/amend authorship before a public push if the repository owner requires a personal identity. The local repository has no configured origin or published release tag.

Before public release:

1. Review `docs/validation.md`, `SECURITY.md`, SYNTHETIC labels and all assets. Confirm repository owner and public visibility, repository name `agent-waste-auditor`, MIT license and release authorization.
2. Create an empty repository under the approved owner and configure its verified URL as origin. No owner URL is guessed in the scaffold.
3. Push only after the user's explicit approval. Run the existing GitHub Actions matrix and inspect every Python/OS job. Local Windows tests do not prove Linux/macOS results.
4. Enable GitHub private vulnerability reporting, decide a maintainer contact, then create an annotated `v0.1.0` tag on the approved commit and publish release notes/assets after approval.
5. Optionally publish to PyPI only under separate explicit authorization and verified project ownership. No PyPI token or paid API is required for local use.

Suggested repository description: `Offline AI agent task cost, failure, rework and value audit CLI + Skill.` Suggested topics: `ai-agents`, `cost-analysis`, `agent-skills`, `codex`, `claude-code`, `python`, `observability`.

## Release notes draft

AgentWaste v0.1.0 — Find the Hidden Cost of AI Work.

First offline CLI/Agent Skill release with generic JSONL/CSV and experimental native log adapters, Decimal pricing with date windows, provenance/currency-separated cost accounting, evidence-based inefficiency review, acceptance-gated ROI and matching-task comparisons. JSON, CSV, Markdown and self-contained HTML reports. Reproducible SYNTHETIC demos and a multi-OS/Python CI workflow are included.

Native profiles are provisional, not a stable provider contract. Unsupported: streaming/aggregate usage formats, subscription invoice reconciliation, FX and automatic human-effort inference. No commercial model prices are bundled. Audit findings require human review and are not billing certification or guaranteed recoverable savings.

Use the local validation record for executed tests. Do not announce the full CI matrix as passing until it runs remotely.
