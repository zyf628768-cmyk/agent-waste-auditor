# AgentWaste — SYNTHETIC

Amounts retain currency and origin. Unknown costs are not zero. Findings are reviewable suspicions.

## Comparison: SYNTHETIC-fix-parser

| Variant | Attempts | Known outcomes | Success rate | Cost per attempt | Cost per success | Human min | Median elapsed s |
| --- | --- | --- | --- | --- | --- | --- | --- |
| claude-code | 1 | 1 | 1 | USD actual=0.04, estimated=0.61, manual=12 | USD actual=0.04, estimated=0.61, manual=12 | 20 | 22 |
| codex | 1 | 1 | 1 | USD actual=0.02, estimated=0.3, manual=6 | USD actual=0.02, estimated=0.3, manual=6 | 10 | 12 |

<details><summary>Structured evidence: Groups</summary>

<pre>[
  {
    &quot;task_key&quot;: &quot;SYNTHETIC-fix-parser&quot;,
    &quot;difficulty&quot;: &quot;easy&quot;,
    &quot;acceptance_id&quot;: &quot;SYNTHETIC-parser-tests-v1&quot;,
    &quot;cost_coverage_complete&quot;: true,
    &quot;coverage_signature&quot;: {
      &quot;human_effort_known&quot;: true,
      &quot;monetary_basis&quot;: [
        &quot;actual&quot;,
        &quot;estimated&quot;
      ],
      &quot;unknown_reasons&quot;: [],
      &quot;currencies&quot;: [
        &quot;USD&quot;
      ]
    },
    &quot;comparable&quot;: true,
    &quot;agents&quot;: [
      {
        &quot;agent&quot;: &quot;claude-code&quot;,
        &quot;dimension&quot;: &quot;agent&quot;,
        &quot;attempts&quot;: 1,
        &quot;known_outcomes&quot;: 1,
        &quot;successes&quot;: 1,
        &quot;unknown_outcomes&quot;: 0,
        &quot;success_rate&quot;: &quot;1&quot;,
        &quot;totals&quot;: {
          &quot;USD&quot;: {
            &quot;actual&quot;: &quot;0.04&quot;,
            &quot;estimated&quot;: &quot;0.61&quot;,
            &quot;manual&quot;: &quot;12&quot;
          }
        },
        &quot;cost_per_attempt&quot;: {
          &quot;USD&quot;: {
            &quot;actual&quot;: &quot;0.04&quot;,
            &quot;estimated&quot;: &quot;0.61&quot;,
            &quot;manual&quot;: &quot;12&quot;
          }
        },
        &quot;cost_per_success&quot;: {
          &quot;USD&quot;: {
            &quot;actual&quot;: &quot;0.04&quot;,
            &quot;estimated&quot;: &quot;0.61&quot;,
            &quot;manual&quot;: &quot;12&quot;
          }
        },
        &quot;human_minutes&quot;: &quot;20&quot;,
        &quot;elapsed_median_seconds&quot;: &quot;22&quot;,
        &quot;elapsed_seconds&quot;: [
          &quot;22&quot;
        ],
        &quot;rework_events&quot;: 0
      },
      {
        &quot;agent&quot;: &quot;codex&quot;,
        &quot;dimension&quot;: &quot;agent&quot;,
        &quot;attempts&quot;: 1,
        &quot;known_outcomes&quot;: 1,
        &quot;successes&quot;: 1,
        &quot;unknown_outcomes&quot;: 0,
        &quot;success_rate&quot;: &quot;1&quot;,
        &quot;totals&quot;: {
          &quot;USD&quot;: {
            &quot;actual&quot;: &quot;0.02&quot;,
            &quot;estimated&quot;: &quot;0.3&quot;,
            &quot;manual&quot;: &quot;6&quot;
          }
        },
        &quot;cost_per_attempt&quot;: {
          &quot;USD&quot;: {
            &quot;actual&quot;: &quot;0.02&quot;,
            &quot;estimated&quot;: &quot;0.3&quot;,
            &quot;manual&quot;: &quot;6&quot;
          }
        },
        &quot;cost_per_success&quot;: {
          &quot;USD&quot;: {
            &quot;actual&quot;: &quot;0.02&quot;,
            &quot;estimated&quot;: &quot;0.3&quot;,
            &quot;manual&quot;: &quot;6&quot;
          }
        },
        &quot;human_minutes&quot;: &quot;10&quot;,
        &quot;elapsed_median_seconds&quot;: &quot;12&quot;,
        &quot;elapsed_seconds&quot;: [
          &quot;12&quot;
        ],
        &quot;rework_events&quot;: 0
      }
    ]
  }
]</pre>
</details>

<details><summary>Structured evidence: Excluded</summary>

<pre>[]</pre>
</details>
