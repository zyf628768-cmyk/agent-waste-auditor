"""Maintain schemas for canonical events/datasets and audit/comparison reports."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "schemas"
DECIMAL = {"type": "string", "pattern": r"^\d+(?:\.\d+)?(?:[eE][+-]?\d+)?$"}
CURRENCY = {"type": "string", "pattern": "^[A-Z]{3}$"}
TOTALS = {"type": "object", "propertyNames": CURRENCY, "additionalProperties": {"type": "object", "required": ["actual", "estimated", "manual"], "additionalProperties": False, "properties": {k: DECIMAL for k in ("actual", "estimated", "manual")}}}


def save(name, schema):
    ROOT.mkdir(exist_ok=True)
    schema = {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": f"https://agentwaste.invalid/schemas/{name}", **schema}
    (ROOT / name).write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")


def main():
    event = {"type": "object", "required": ["schema_version", "id", "task_id", "agent", "timestamp", "kind"], "additionalProperties": False,
             "properties": {"schema_version": {"const": "1.0"}, **{k: {"type": "string", "minLength": 1} for k in ("id", "task_id", "agent", "model", "action")},
             "timestamp": {"type": "string", "format": "date-time"}, "kind": {"enum": ["model", "tool", "human", "wait", "task"]},
             "status": {"enum": ["success", "failed", "timeout", "unknown", "running"]},
             "category": {"enum": ["model", "tool", "failure", "rework", "wait", "quality"]},
             "origin": {"enum": ["actual", "estimated", "manual"]}, "amount": DECIMAL, "currency": CURRENCY,
             "retry_reason": {"enum": ["unknown", "transient", "user_requested", "idempotent_check"]},
             **{k: {"type": "integer", "minimum": 0} for k in ("input_tokens", "output_tokens", "cached_tokens", "cache_write_tokens", "duration_ms", "queue_ms", "human_wait_ms", "source_line")},
             **{k: {"type": "boolean"} for k in ("synthetic", "progress")},
             **{k: {"type": "string", "pattern": "^[a-f0-9]{64}$"} for k in ("signature", "context_signature")}},
             "dependentRequired": {"amount": ["currency", "origin"]}}
    save("event.schema.json", event)
    save("dataset.schema.json", {"type": "object", "required": ["schema_version", "events", "tasks", "warnings"], "properties": {"schema_version": {"const": "1.0"}, "events": {"type": "array", "items": event}, "tasks": {"type": "array", "items": {"type": "object", "required": ["task_id"]}}, "warnings": {"type": "array", "items": {"type": "string"}}}})
    charge = {"type": "object", "required": ["event_id", "task_id", "category", "amount", "origin", "currency"], "additionalProperties": False,
              "properties": {"amount": DECIMAL, "currency": CURRENCY, "origin": {"enum": ["actual", "estimated", "manual"]}, "source": {"enum": ["event", "task_metadata"]}, "category": {"enum": ["model", "tool", "human", "failure", "rework", "wait", "quality"]}, **{k: {"type": "string"} for k in ("event_id", "task_id", "price_id")}, "failed": {"type": "boolean"}}}
    evidence = {"type": "object", "required": ["event_id", "source_line", "status", "signature"], "properties": {"event_id": {"type": "string"}, "source_line": {"type": ["integer", "null"]}, "status": {"type": "string"}, "signature": {"type": ["string", "null"]}}}
    task = {"type": "object", "required": ["task_id", "agent", "status", "totals", "unknown_costs", "roi", "cost_coverage"], "properties": {"task_id": {"type": "string"}, "agent": {"type": "string"}, "status": {"enum": ["success", "failed", "running", "unknown"]}, "totals": TOTALS, "unknown_costs": {"type": "array"}, "cost_coverage": {"type": "object", "required": ["known_events", "cost_bearing_events", "complete"], "properties": {"complete": {"type": "boolean"}, "known_events": {"type": "integer", "minimum": 0}, "cost_bearing_events": {"type": "integer", "minimum": 0}}}, "roi": {"type": "object", "required": ["status"], "properties": {"status": {"enum": ["unavailable", "scenario_estimate", "verified_basis"]}}}}}
    finding = {"type": "object", "required": ["rule", "task_id", "conclusion", "explanation", "recommendation", "evidence"], "properties": {"conclusion": {"const": "suspected_inefficiency"}, "evidence": {"type": "array", "minItems": 1, "items": evidence}}}
    save("audit.schema.json", {"type": "object", "additionalProperties": False, "required": ["schema_version", "report_type", "synthetic", "totals", "tasks", "charges", "findings", "coverage", "timeline", "trend", "high_cost_steps", "successful_tasks", "average_cost_per_success", "average_cost_definition"],
         "properties": {"schema_version": {"const": "1.0"}, "report_type": {"const": "audit"}, "synthetic": {"type": "boolean"}, "totals": TOTALS, "tasks": {"type": "array", "items": task}, "charges": {"type": "array", "items": charge}, "findings": {"type": "array", "items": finding}, "coverage": {"type": "object", "required": ["events", "tasks", "unknown_cost_items", "warnings", "scope"]}, "timeline": {"type": "array", "items": {"type": "object", "required": ["id", "task_id", "timestamp", "kind"]}}, "trend": {"type": "array", "items": {"type": "object", "required": ["date_utc", "totals"], "properties": {"totals": TOTALS}}}, "high_cost_steps": {"type": "array", "items": charge}, "successful_tasks": {"type": "integer", "minimum": 0}, "average_cost_per_success": {"type": ["object", "null"], "additionalProperties": DECIMAL}, "average_cost_definition": {"type": "string"}}})
    save("comparison.schema.json", {"type": "object", "required": ["schema_version", "report_type", "groups", "excluded", "caution"], "properties": {"schema_version": {"const": "1.0"}, "report_type": {"const": "comparison"}, "groups": {"type": "array", "items": {"type": "object", "required": ["task_key", "difficulty", "acceptance_id", "cost_coverage_complete", "comparable", "agents"]}}, "excluded": {"type": "array"}, "caution": {"type": "string"}}})
    print("Schemas generated")


if __name__ == "__main__":
    main()
