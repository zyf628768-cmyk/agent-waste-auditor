# AgentWaste — SYNTHETIC

Amounts retain currency and origin. Unknown costs are not zero. Findings are reviewable suspicions.

## Totals

<pre>{
  &quot;USD&quot;: {
    &quot;actual&quot;: &quot;0.04&quot;,
    &quot;estimated&quot;: &quot;0.61&quot;,
    &quot;manual&quot;: &quot;12&quot;
  }
}</pre>

## Coverage

<pre>{
  &quot;events&quot;: 3,
  &quot;tasks&quot;: 1,
  &quot;unknown_cost_items&quot;: 0,
  &quot;warnings&quot;: [],
  &quot;scope&quot;: &quot;specified files only; unobserved costs cannot be inferred&quot;
}</pre>

## Tasks

<pre>[
  {
    &quot;task_id&quot;: &quot;SYNTHETIC-claude&quot;,
    &quot;agent&quot;: &quot;claude-code&quot;,
    &quot;task_key&quot;: &quot;SYNTHETIC-fix-parser&quot;,
    &quot;difficulty&quot;: &quot;easy&quot;,
    &quot;acceptance_id&quot;: &quot;SYNTHETIC-parser-tests-v1&quot;,
    &quot;model&quot;: &quot;SYNTHETIC-model&quot;,
    &quot;prompt_strategy&quot;: null,
    &quot;workflow&quot;: null,
    &quot;status&quot;: &quot;success&quot;,
    &quot;accepted&quot;: true,
    &quot;synthetic&quot;: true,
    &quot;human_minutes&quot;: &quot;20&quot;,
    &quot;rework_minutes&quot;: &quot;0&quot;,
    &quot;totals&quot;: {
      &quot;USD&quot;: {
        &quot;actual&quot;: &quot;0.04&quot;,
        &quot;estimated&quot;: &quot;0.61&quot;,
        &quot;manual&quot;: &quot;12&quot;
      }
    },
    &quot;category_totals&quot;: {
      &quot;human&quot;: {
        &quot;USD&quot;: {
          &quot;actual&quot;: &quot;0&quot;,
          &quot;estimated&quot;: &quot;0&quot;,
          &quot;manual&quot;: &quot;12&quot;
        }
      },
      &quot;model&quot;: {
        &quot;USD&quot;: {
          &quot;actual&quot;: &quot;0&quot;,
          &quot;estimated&quot;: &quot;0.61&quot;,
          &quot;manual&quot;: &quot;0&quot;
        }
      },
      &quot;rework&quot;: {
        &quot;USD&quot;: {
          &quot;actual&quot;: &quot;0&quot;,
          &quot;estimated&quot;: &quot;0&quot;,
          &quot;manual&quot;: &quot;0&quot;
        }
      },
      &quot;tool&quot;: {
        &quot;USD&quot;: {
          &quot;actual&quot;: &quot;0.04&quot;,
          &quot;estimated&quot;: &quot;0&quot;,
          &quot;manual&quot;: &quot;0&quot;
        }
      }
    },
    &quot;failed_step_costs&quot;: {},
    &quot;unknown_costs&quot;: [],
    &quot;cost_coverage&quot;: {
      &quot;known_events&quot;: 2,
      &quot;cost_bearing_events&quot;: 2,
      &quot;complete&quot;: true
    },
    &quot;elapsed_seconds&quot;: &quot;22.0&quot;,
    &quot;duration_sum_ms&quot;: 0,
    &quot;queue_ms&quot;: 0,
    &quot;human_wait_ms&quot;: 0,
    &quot;rework_events&quot;: 0,
    &quot;roi&quot;: {
      &quot;status&quot;: &quot;scenario_estimate&quot;,
      &quot;currency&quot;: &quot;USD&quot;,
      &quot;baseline_cost&quot;: &quot;36&quot;,
      &quot;total_cost&quot;: &quot;12.65&quot;,
      &quot;net_savings&quot;: &quot;23.35&quot;,
      &quot;roi&quot;: &quot;1.845849802371541501976284585&quot;,
      &quot;assumptions&quot;: [
        &quot;user-entered baseline and human effort&quot;,
        &quot;rework minutes exclude other human minutes&quot;,
        &quot;ROI = (baseline - task cost) / task cost; zero cost has undefined ROI&quot;
      ]
    }
  }
]</pre>

## Findings

<pre>[]</pre>

## High Cost Steps

<pre>[
  {
    &quot;amount&quot;: &quot;0.61&quot;,
    &quot;currency&quot;: &quot;USD&quot;,
    &quot;origin&quot;: &quot;estimated&quot;,
    &quot;price_id&quot;: &quot;SYNTHETIC-2026-v1&quot;,
    &quot;event_id&quot;: &quot;SYNTHETIC-c-model&quot;,
    &quot;task_id&quot;: &quot;SYNTHETIC-claude&quot;,
    &quot;category&quot;: &quot;model&quot;,
    &quot;failed&quot;: false,
    &quot;source&quot;: &quot;event&quot;
  },
  {
    &quot;amount&quot;: &quot;0.04&quot;,
    &quot;origin&quot;: &quot;actual&quot;,
    &quot;currency&quot;: &quot;USD&quot;,
    &quot;event_id&quot;: &quot;SYNTHETIC-c-tool&quot;,
    &quot;task_id&quot;: &quot;SYNTHETIC-claude&quot;,
    &quot;category&quot;: &quot;tool&quot;,
    &quot;failed&quot;: false,
    &quot;source&quot;: &quot;event&quot;
  }
]</pre>

## Trend

<pre>[
  {
    &quot;date_utc&quot;: &quot;2026-10-01&quot;,
    &quot;totals&quot;: {
      &quot;USD&quot;: {
        &quot;actual&quot;: &quot;0.04&quot;,
        &quot;estimated&quot;: &quot;0.61&quot;,
        &quot;manual&quot;: &quot;0&quot;
      }
    }
  }
]</pre>

## Timeline

<pre>[
  {
    &quot;id&quot;: &quot;SYNTHETIC-c-model&quot;,
    &quot;task_id&quot;: &quot;SYNTHETIC-claude&quot;,
    &quot;timestamp&quot;: &quot;2026-10-01T09:00:00Z&quot;,
    &quot;kind&quot;: &quot;model&quot;,
    &quot;status&quot;: &quot;success&quot;
  },
  {
    &quot;id&quot;: &quot;SYNTHETIC-c-tool&quot;,
    &quot;task_id&quot;: &quot;SYNTHETIC-claude&quot;,
    &quot;timestamp&quot;: &quot;2026-10-01T09:00:10Z&quot;,
    &quot;kind&quot;: &quot;tool&quot;,
    &quot;status&quot;: &quot;success&quot;
  },
  {
    &quot;id&quot;: &quot;SYNTHETIC-c-end&quot;,
    &quot;task_id&quot;: &quot;SYNTHETIC-claude&quot;,
    &quot;timestamp&quot;: &quot;2026-10-01T09:00:22Z&quot;,
    &quot;kind&quot;: &quot;task&quot;,
    &quot;status&quot;: &quot;success&quot;
  }
]</pre>
