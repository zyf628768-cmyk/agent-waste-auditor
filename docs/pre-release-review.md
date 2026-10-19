# Pre-release review and corrections

This review preceded the first public v0.1.0 release. All reproductions use SYNTHETIC data and are in `tests/test_refinements.py` alongside the original audit suite. The review does not certify universal native format compatibility or make an independent billing assertion.

| Area | Discovered risk | Correction and observable verification |
| --- | --- | --- |
| Input integrity | Duplicate JSON keys, inconsistent CSV widths/headers, nonfinite constants or extreme nesting could be silently accepted or crash parsing | Bounded parser with safe codes/line references; malformed/Unicode/duplicate-key regression cases |
| Identity/privacy | A key regex matched the `sk-` substring inside `task-12`, merging task labels; truncation or redaction could also merge identities | Token boundary fix, bounded labels instead of truncation, normalized collision rejection, named-secret redaction before argument hashing; 10,000-event benchmark asserts 100 distinct tasks |
| Native usage | Partial positive Claude cache counters could fail instead of remaining unknown; missing usage calls could be omitted | Partial counts retained as evidence, explicit unknown model events, snapshot conflict/regression checks, conservative Codex gap/model attribution |
| Financial arithmetic | A caller's Decimal precision and floating elapsed-seconds conversion could alter results | Local 128-digit arithmetic contexts, exact timedelta-to-Decimal conversion, UTC dated pricing, indexed non-overlapping price lookup |
| ROI provenance | A zero-valued estimate could be labeled verified | Any estimated charge origin retains scenario status; status/acceptance and complete ROI evidence checks |
| Comparison fairness | Unequal attempt totals, different cost bases/human coverage and explicitly failed tasks lacking acceptance could mislead | Coverage/basis/currency grouping; per-attempt/per-success costs, known-failure denominators, unknown outcome count and median observed duration |
| Detection | Far-apart calls or calls separated by progress could be joined; every currency shared a one-unit threshold; unknown task markers could clear failure | Configurable windows/count/context/currency thresholds, progress/check barriers, explicit reopening, no known-zero post-failure spend |
| Report integrity | Shallow type checks accepted incomplete nested economics; failed writes could truncate old reports; comparison CSV was empty | Shared strict schemas, financial/evidence/count consistency checks, atomic replacement, useful comparison CSV and Markdown summaries; injection/failed-write regression tests |
| Scale | Event coverage and daily totals repeatedly rescanned all charges | Indexed IDs and grouped daily/currency accumulation; measured synthetic workload with explicit financial/identity invariants |
| Installation/release | Tests could accidentally import checkout code; a valid old ZIP could be published for a new commit | Isolated installed-wheel smoke; clean-tree packaging from Git blobs; ZIP commit/CRC/membership, wheel/sdist code and SHA checks; exact-commit 12-job CI gate |

Executed local results, installed-artifact evidence, performance measurements and remote CI status are kept separate in `docs/validation.md` and release verification outputs. Previously unsupported streaming/aggregate/unknown native formats and subscription/FX inference remain explicitly unsupported rather than being guessed into estimates.
