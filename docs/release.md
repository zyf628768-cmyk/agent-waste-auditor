# v0.1.0 release procedure

Local release assets: source ZIP, source distribution, universal Python wheel, SHA256SUMS.txt, release notes, test log and CLI evidence. ZIP includes source/docs/tests/fixtures/reports, excluding `.git`, caches, build output and private data. `scripts/package_release.py` generates deterministic source ZIP membership and integrity checks. No remote repository or public release is created automatically.

Local Git history uses the project placeholder author `AgentWaste Development <agentwaste@example.invalid>`, without changing global Git identity. Review/amend authorship before a public push if the repository owner requires a personal identity. The local repository has no configured origin or published release tag.

This describes the prepublication snapshot. The user subsequently authorized optimization followed by publication to `zyf628768-cmyk/agent-waste-auditor`, including the required workflow OAuth scope. Authentication still requires the user's normal GitHub device authorization; no credentials are embedded in this project. Consult the actual GitHub Release and publication evidence for live remote state.

After reviewing/committing final validation evidence and building artifacts:

```sh
python scripts/package_release.py
python scripts/verify_release.py
python scripts/publish.py --repo zyf628768-cmyk/agent-waste-auditor
# The previous command is a local plan only. After authenticated authorization:
python scripts/publish.py --repo zyf628768-cmyk/agent-waste-auditor --execute
```

The publisher checks clean source, checksums and ZIP commit identity, verifies the authenticated owner, creates the public repository only if absent, preserves existing origin/visibility, uses a process-scoped Git credential helper, pushes without force, waits for `tests.yml` on the exact commit, checks all 12 matrix jobs, and only then tags/publishes verified assets. Any failure stops publication; no old tag, existing repository history or visibility is overwritten. It does not request/store/display secrets itself or configure a global Git identity/helper. `docs/RELEASE_NOTES.md` is the release notes file.

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
