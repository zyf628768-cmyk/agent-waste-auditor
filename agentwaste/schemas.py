"""Shared strict interchange schemas and dependency-free structural validation.

The validator implements the keywords used here, not arbitrary JSON Schema.
Tests additionally validate these documents with Draft202012Validator.
"""
import re
from .models import timestamp, money
from .safeio import InputError

STR = {"type": "string"}
LABEL = {"type": "string", "minLength": 1, "maxLength": 160}
BOOL = {"type": "boolean"}
COUNT = {"type": "integer", "minimum": 0}
DECIMAL = {"type": "string", "pattern": r"^\d+(?:\.\d+)?(?:[eE][+-]?\d+)?$", "format": "money"}
SIGNED = {"type": "string", "pattern": r"^-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?$"}
CURRENCY = {"type": "string", "pattern": "^[A-Z]{3}$"}
ORIGIN = {"enum": ["actual", "estimated", "manual"]}
CATEGORY = {"enum": ["model", "tool", "human", "failure", "rework", "wait", "quality"]}
STATUS = {"enum": ["success", "failed", "timeout", "unknown", "running"]}
TASK_STATUS = {"enum": ["success", "failed", "unknown", "running"]}


def array(item):
    return {"type": "array", "items": item}


def nullable(schema):
    return {"anyOf": [schema, {"type": "null"}]}


def obj(properties, required=None):
    return {"type": "object", "additionalProperties": False, "properties": properties,
            "required": list(properties) if required is None else required}


TOTALS = {"type": "object", "propertyNames": CURRENCY,
          "additionalProperties": obj({k: DECIMAL for k in ("actual", "estimated", "manual")})}
EVENT = obj({"schema_version": {"const": "1.0"}, **{k: LABEL for k in ("id", "task_id", "agent", "model", "action")},
             "timestamp": {"type": "string", "format": "date-time"}, "kind": {"enum": ["model", "tool", "human", "wait", "task"]},
             "status": STATUS, "category": CATEGORY, "origin": ORIGIN, "amount": DECIMAL, "currency": CURRENCY,
             "retry_reason": {"enum": ["unknown", "transient", "user_requested", "idempotent_check"]},
             **{k: COUNT for k in ("input_tokens", "output_tokens", "cached_tokens", "cache_write_tokens", "duration_ms", "queue_ms", "human_wait_ms", "source_line")},
             **{k: BOOL for k in ("synthetic", "progress", "usage_complete")},
             **{k: {"type": "string", "pattern": "^[a-f0-9]{64}$"} for k in ("signature", "context_signature")}},
            ["schema_version", "id", "task_id", "agent", "timestamp", "kind"])
EVENT["dependentRequired"] = {"amount": ["currency", "origin"]}
TASK_INPUT = obj({**{k: LABEL for k in ("task_id", "agent", "task_key", "difficulty", "acceptance_id", "model", "prompt_strategy", "workflow")},
                  "status": TASK_STATUS, **{k: BOOL for k in ("accepted", "baseline_verified", "synthetic")},
                  **{k: DECIMAL for k in ("baseline_minutes", "human_minutes", "rework_minutes", "hourly_rate")}, "currency": CURRENCY}, ["task_id"])
TASK_INPUT["dependentRequired"] = {"hourly_rate": ["currency"]}
DATASET = obj({"schema_version": {"const": "1.0"}, "events": array(EVENT), "tasks": array(TASK_INPUT),
               "warnings": array(STR), "source_format": {"enum": ["jsonl", "csv", "codex", "claude", "openai"]},
               "profile": LABEL, "source_records": COUNT}, ["schema_version", "events", "tasks", "warnings"])
PRICE = obj({**{k: LABEL for k in ("id", "model")}, "currency": CURRENCY, "source": {"type": "string", "minLength": 1, "maxLength": 2048},
             **{k: {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}$"} for k in ("effective_from", "effective_to")},
             **{k: DECIMAL for k in ("input_per_million", "output_per_million", "cache_read_per_million", "cache_write_per_million")}},
            ["id", "model", "currency", "source", "effective_from", "effective_to", "input_per_million", "output_per_million"])
PRICING = obj({"schema_version": {"const": "1.0"}, "prices": array(PRICE)})
CHARGE = obj({"amount": DECIMAL, "currency": CURRENCY, "origin": ORIGIN, "category": CATEGORY,
              **{k: LABEL for k in ("event_id", "task_id", "price_id")}, "failed": BOOL,
              "source": {"enum": ["event", "task_metadata"]}}, ["amount", "currency", "origin", "category", "event_id", "task_id", "source"])
EVIDENCE = obj({"event_id": LABEL, "source_line": nullable(COUNT), "status": STATUS,
                "signature": nullable({"type": "string", "pattern": "^[a-f0-9]{64}$"})})
FINDING = obj({"rule": STR, "severity": {"const": "review"}, "task_id": LABEL, "conclusion": {"const": "suspected_inefficiency"},
               "explanation": STR, "recommendation": STR, "evidence": {**array(EVIDENCE), "minItems": 1}})
ROI = {"anyOf": [obj({"status": {"const": "unavailable"}, "reason": STR}),
                  obj({"status": {"enum": ["scenario_estimate", "verified_basis"]}, "currency": CURRENCY,
                       "baseline_cost": DECIMAL, "total_cost": DECIMAL, "net_savings": SIGNED, "roi": nullable(SIGNED), "assumptions": array(STR)})]}
COST_COVERAGE = obj({"known_events": COUNT, "cost_bearing_events": COUNT, "complete": BOOL, "human_effort_known": BOOL,
                     "monetary_basis": array(ORIGIN), "unknown_reasons": array(STR)})
TASK_REPORT = obj({**{k: LABEL for k in ("task_id", "agent")},
                   **{k: nullable(LABEL) for k in ("task_key", "difficulty", "acceptance_id", "model", "prompt_strategy", "workflow")},
                   "status": TASK_STATUS, "accepted": nullable(BOOL), "synthetic": BOOL,
                   **{k: nullable(DECIMAL) for k in ("human_minutes", "rework_minutes", "elapsed_seconds")},
                   "totals": TOTALS, "category_totals": {"type": "object", "propertyNames": CATEGORY, "additionalProperties": TOTALS},
                   "failed_step_costs": TOTALS, "unknown_costs": array(obj({"event_id": LABEL, "reason": STR})),
                   "cost_coverage": COST_COVERAGE, **{k: COUNT for k in ("duration_sum_ms", "queue_ms", "human_wait_ms", "rework_events")}, "roi": ROI})
TIMELINE = obj({"id": LABEL, "task_id": LABEL, "timestamp": {"type": "string", "format": "date-time"},
                "kind": {"enum": ["model", "tool", "human", "wait", "task"]}, "status": STATUS}, ["id", "task_id", "timestamp", "kind"])
AUDIT = obj({"schema_version": {"const": "1.0"}, "report_type": {"const": "audit"}, "synthetic": BOOL,
             "analysis_settings": obj({"schema_version": {"const": "1.0"}, "repetition_threshold": COUNT, "window_seconds": COUNT, "context_tokens": COUNT, "high_cost_thresholds": {"type": "object", "propertyNames": CURRENCY, "additionalProperties": DECIMAL}}),
             "totals": TOTALS, "tasks": array(TASK_REPORT), "charges": array(CHARGE), "findings": array(FINDING),
             "coverage": obj({"events": COUNT, "tasks": COUNT, "unknown_cost_items": COUNT, "warnings": array(STR), "scope": STR}),
             "timeline": array(TIMELINE), "trend": array(obj({"date_utc": STR, "totals": TOTALS})),
             "high_cost_steps": array(CHARGE), "successful_tasks": COUNT,
             "average_cost_per_success": nullable({"type": "object", "propertyNames": CURRENCY, "additionalProperties": DECIMAL}),
             "average_cost_definition": STR})
VARIANT = obj({"agent": LABEL, "dimension": {"enum": ["agent", "model", "prompt_strategy", "workflow"]},
               **{k: COUNT for k in ("attempts", "known_outcomes", "successes", "unknown_outcomes", "rework_events")},
               "success_rate": nullable(DECIMAL), "totals": TOTALS, "cost_per_attempt": TOTALS, "cost_per_success": nullable(TOTALS),
               "human_minutes": nullable(DECIMAL), "elapsed_median_seconds": nullable(DECIMAL), "elapsed_seconds": array(nullable(DECIMAL))})
GROUP = obj({"task_key": LABEL, "difficulty": LABEL, "acceptance_id": LABEL, "cost_coverage_complete": BOOL,
             "coverage_signature": obj({"human_effort_known": BOOL, "monetary_basis": array(ORIGIN), "unknown_reasons": array(STR), "currencies": array(CURRENCY)}),
             "comparable": BOOL, "agents": array(VARIANT)})
COMPARISON = obj({"schema_version": {"const": "1.0"}, "report_type": {"const": "comparison"}, "synthetic": BOOL,
                  "dimension": {"enum": ["agent", "model", "prompt_strategy", "workflow"]}, "groups": array(GROUP),
                  "excluded": array(obj({"task_id": LABEL, "reason": STR})), "caution": STR})
SCHEMAS = {"event": EVENT, "dataset": DATASET, "tasks": array(TASK_INPUT), "pricing": PRICING, "audit": AUDIT, "comparison": COMPARISON}


def validate(value, schema):
    """Validate only our schema subset; no remote references or dependencies."""
    if "anyOf" in schema:
        for alternative in schema["anyOf"]:
            try:
                validate(value, alternative)
                return
            except (InputError, ValueError):
                pass
        raise InputError("SCHEMA_TYPE_MISMATCH")
    if "const" in schema and (type(value) is not type(schema["const"]) or value != schema["const"]):
        raise InputError("SCHEMA_CONST_MISMATCH")
    if "enum" in schema and not any(type(value) is type(x) and value == x for x in schema["enum"]):
        raise InputError("SCHEMA_ENUM_MISMATCH")
    types = {"object": dict, "array": list, "string": str, "integer": int, "boolean": bool, "null": type(None)}
    if "type" in schema and type(value) is not types[schema["type"]]:
        raise InputError("SCHEMA_TYPE_MISMATCH")
    if isinstance(value, dict):
        props = schema.get("properties", {})
        if any(k not in value for k in schema.get("required", [])):
            raise InputError("SCHEMA_REQUIRED_FIELD")
        for key, item in value.items():
            if "propertyNames" in schema:
                validate(key, schema["propertyNames"])
            if key in props:
                validate(item, props[key])
            elif schema.get("additionalProperties") is False:
                raise InputError("SCHEMA_UNKNOWN_FIELD")
            elif isinstance(schema.get("additionalProperties"), dict):
                validate(item, schema["additionalProperties"])
        for field, dependencies in schema.get("dependentRequired", {}).items():
            if field in value and any(d not in value for d in dependencies):
                raise InputError("SCHEMA_REQUIRED_FIELD")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            raise InputError("SCHEMA_ARRAY_SIZE")
        for item in value:
            validate(item, schema.get("items", {}))
    if isinstance(value, str):
        if not schema.get("minLength", 0) <= len(value) <= schema.get("maxLength", 100_000_000):
            raise InputError("SCHEMA_STRING_SIZE")
        if "pattern" in schema and re.search(schema["pattern"], value) is None:
            raise InputError("SCHEMA_STRING_FORMAT")
        if schema.get("format") == "money":
            money(value)
        if schema.get("format") == "date-time":
            timestamp(value)
    if type(value) is int and value < schema.get("minimum", value):
        raise InputError("SCHEMA_NUMBER_RANGE")


def validate_report(data):
    if not isinstance(data, dict) or data.get("report_type") not in {"audit", "comparison"}:
        raise InputError("REPORT_TYPE_REQUIRED")
    validate(data, SCHEMAS[data["report_type"]])
    if data["report_type"] == "audit":
        from .costs import aggregate
        from .rules import Rules
        Rules.from_dict(data["analysis_settings"])
        def same_totals(left, right):
            return {cur: {origin: money(value) for origin, value in bucket.items()} for cur, bucket in left.items()} == {cur: {origin: money(value) for origin, value in bucket.items()} for cur, bucket in right.items()}
        if not same_totals(aggregate(data["charges"]), data["totals"]):
            raise InputError("REPORT_TOTAL_MISMATCH")
        ids = {e["id"]: e["task_id"] for e in data["timeline"]}
        task_ids = {t["task_id"] for t in data["tasks"]}
        if len(ids) != len(data["timeline"]) or len(task_ids) != len(data["tasks"]):
            raise InputError("REPORT_DUPLICATE_ID")
        if any(c["task_id"] not in task_ids or (c["source"] == "event" and ids.get(c["event_id"]) != c["task_id"]) for c in data["charges"]):
            raise InputError("REPORT_CHARGE_IDENTITY_MISMATCH")
        task_charges = {}
        for charge in data["charges"]:
            task_charges.setdefault(charge["task_id"], []).append(charge)
        for task in data["tasks"]:
            if not same_totals(aggregate(task_charges.get(task["task_id"], [])), task["totals"]):
                raise InputError("REPORT_TASK_TOTAL_MISMATCH")
            if task["accepted"] is True and task["status"] != "success":
                raise InputError("REPORT_ACCEPTANCE_MISMATCH")
        if data["coverage"]["events"] != len(data["timeline"]) or data["coverage"]["tasks"] != len(data["tasks"]) or data["coverage"]["unknown_cost_items"] != sum(len(t["unknown_costs"]) for t in data["tasks"]):
            raise InputError("REPORT_COVERAGE_MISMATCH")
        if any(e["event_id"] not in ids for finding in data["findings"] for e in finding["evidence"]):
            raise InputError("REPORT_EVIDENCE_MISMATCH")
    else:
        for group in data["groups"]:
            for variant in group["agents"]:
                if not variant["successes"] <= variant["known_outcomes"] <= variant["attempts"] or variant["unknown_outcomes"] != variant["attempts"] - variant["known_outcomes"]:
                    raise InputError("REPORT_OUTCOME_COUNT_MISMATCH")
