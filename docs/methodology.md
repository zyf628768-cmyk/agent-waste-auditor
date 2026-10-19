# Audit methodology

Financial quantities are Python Decimal, represented without forced cent rounding. No FX conversion, interest, taxes, minimum bill increment, subscription allocation, speculative token estimation or autonomous price fetching. An explicit event charge wins over token estimation for that event. `actual` is reported spend, `estimated` uses exact known rates, `manual` is entered by the user. They are never silently merged in the accounting buckets. Reports may show a same-currency observed total for task ROI with its assumptions retained.

Six cost categories are supported as explicit event classifications. Model/tool are default component categories; failure handling/rework/wait/quality costs can be entered when evidenced. Failed-step attribution overlaps these components and is never added a second time. Human task costs are manual labor components, with rework separate. Missing monetary valuation for recorded human effort produces an unknown item; unrecorded human work remains outside observed scope. Human charge events cannot be combined with task-based labor without reconciliation. An uncharged wait marker is duration evidence, not a known monetary charge.

ROI needs successful accepted output, entered baseline/effort, rate, consistent currency and no known cost gaps. User-declared baseline verification cannot establish a counterfactual scientifically. `verified_basis` is a provenance label; the tool does not verify timesheets or invoices. Scenario ROI is not a guaranteed saving. No accepted output means ROI unavailable even if a baseline was entered. Cost per success uses **all** observed attempt costs including failures divided by accepted successes, per currency, and is unavailable when any observed monetary cost is unknown. Zero successes yield null.

## Rules

All findings have `suspected_inefficiency` conclusion, event IDs, source line references and advice. Counts are not additive dollar savings. Same events can appear in more than one rule.

| Rule | Evidence threshold | Caveat |
| --- | --- | --- |
| repeated_failure | ≥3 same tool/action+argument digest, failed/timeout | Transient retry can be reasonable |
| repeated_read | ≥3 same read action/digest | File may have changed |
| repeated_call | ≥3 same action/digest | Deliberate checks may be required |
| unverified_rework | ≥3 edit/write/patch action/digest and explicit progress=false | A different patch has a different digest; not full semantic diff analysis |
| alternating_loop | consecutive A/B/A/B/A/B tool digests | Human review of termination intent required |
| context_reload | ≥3 same context digests, ≥10,000 input tokens each | Only available when context digest supplied; cache/intention may justify reuse |
| cost_after_failure | cost-bearing event after explicit failed-task event, before another task marker | Native task failure is not inferred |
| cost_without_progress | explicit/estimated charge ≥1 original currency unit and explicit progress=false | Currency-dependent heuristic; not an economic equivalence threshold |

Ordinary repeated-call/read/edit/failure rules exclude events with declared transient/user-requested/idempotent-check reasons or explicit verified progress. Loops also require all six events without those exemptions. Context and post-failure rules remain review prompts; evidence does not prove avoidability. Failed calls with no status evidence cannot trigger repeated_failure. Source annotations can be wrong, and native tool outputs are deliberately not interpreted as trustworthy executable/status instructions.

No cross-task signatures are compared. Fingerprints are stable only for equivalent normalized JSON arguments; differently formatted shell strings may not match. Rework based on multiple different patches, semantic acceptance and whether unchanged files were re-read require external evidence and are not inferred. Rule thresholds are fixed in v0.1.0, not learned or calibrated for different workloads. High-cost steps are top 20 observed event charges **per currency**, without comparing currencies; manual task labor is shown in task components instead. Daily charts use UTC and omit undated task-level human allocations; financial task totals still include them.

Elapsed seconds cover first to last observed timestamps; missing start/end makes this a lower/partial observation, not guaranteed full task duration. Duration sums may overlap. Queue and human waiting are separately supplied measurements and never inferred wages.

Comparisons group exact task key, difficulty, acceptance ID and complete/partial observed financial coverage. Native-derived tasks lack acceptance and are excluded until the user adds it. Aggregate status metrics use known outcomes only; report attempts and known outcomes together. Cost distributions and task durations are descriptive; a synthetic or tiny sample cannot support a model ranking. The caller must ensure matching workload sizes, environment, scope and reliable acceptance.
