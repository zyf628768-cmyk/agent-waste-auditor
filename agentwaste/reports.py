import csv
import html
import json
import io
from pathlib import Path
from decimal import Decimal
from .safeio import atomic_write


def table(headers, rows):
    def cell(value):
        return html.escape(str(value if value is not None else "unavailable"))
    return '<div style="overflow:auto"><table><thead><tr>' + ''.join('<th>' + cell(h) + '</th>' for h in headers) + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join('<td>' + cell(v) + '</td>' for v in row) + '</tr>' for row in rows) + '</tbody></table></div>'


def amounts(values):
    return '; '.join(cur + ' ' + ', '.join(origin + '=' + str(amount) for origin, amount in bucket.items()) for cur, bucket in values.items()) or 'No known monetary charges'


def markdown_summary(data):
    def cell(value):
        text = html.escape(str(value if value is not None else "unavailable")).replace("|", "&#124;").replace("`", "&#96;").replace("\n", " ")
        for character in ('\\', '[', ']', '(', ')', '*', '_', '!'):
            text = text.replace(character, '\\' + character)
        return text
    def mdtable(headers, rows):
        return '\n'.join(['| ' + ' | '.join(map(cell, headers)) + ' |', '| ' + ' | '.join('---' for _ in headers) + ' |', *['| ' + ' | '.join(map(cell, row)) + ' |' for row in rows]])
    parts = []
    if data.get('tasks'):
        parts.extend(['## Task economics', mdtable(['Task', 'Agent', 'Accepted', 'Cost by source', 'Unknown cost items', 'ROI'],
                      [[t['task_id'], t['agent'], t['accepted'], amounts(t['totals']), len(t['unknown_costs']), t['roi']['status']] for t in data['tasks']])])
    if data.get('findings'):
        parts.extend(['## Suspected inefficiency', mdtable(['Rule', 'Evidence (event : source line)', 'Action'],
                      [[f['rule'], '; '.join(e['event_id'] + ' : ' + str(e['source_line']) for e in f['evidence']), f['recommendation']] for f in data['findings']])])
    for group in data.get('groups', []):
        parts.extend(['## Comparison: ' + cell(group['task_key']),
                      mdtable(['Variant', 'Attempts', 'Known outcomes', 'Success rate', 'Cost per attempt', 'Cost per success', 'Human min', 'Median elapsed s'],
                              [[a['agent'], a['attempts'], a['known_outcomes'], a['success_rate'], amounts(a['cost_per_attempt']), amounts(a['cost_per_success']) if a['cost_per_success'] else None, a['human_minutes'], a['elapsed_median_seconds']] for a in group['agents']])])
    return '\n\n'.join(parts)


def readable(data):
    totals = amounts
    body = ['<style>table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:12px;border:1px solid #3b4c60;text-align:left;vertical-align:top;overflow-wrap:anywhere}th{color:#6ce5bc}h2{margin-top:36px}</style>']
    tasks = data.get("tasks", [])
    if tasks:
        body.append('<h2>Tasks, acceptance and observed cost</h2>')
        body.append(table(['Task / Agent', 'Outcome / acceptance', 'Cost by origin', 'Unknown costs', 'Human + rework min', 'Observed elapsed s', 'ROI status'],
                          [[t['task_id'] + ' / ' + t['agent'], t['status'] + ' / ' + str(t['accepted']), totals(t['totals']), len(t['unknown_costs']), str(t['human_minutes']) + ' + ' + str(t['rework_minutes']), t['elapsed_seconds'], t['roi']['status']] for t in tasks]))
    for group in data.get('groups', []):
        body.append('<h2>Comparison: ' + html.escape(group['task_key']) + '</h2><p>Difficulty: ' + html.escape(group['difficulty']) + '; Acceptance: ' + html.escape(group['acceptance_id']) + '; complete observed coverage: ' + str(group['cost_coverage_complete']) + '</p>')
        body.append(table(['Variant', 'Attempts / known outcomes', 'Success rate', 'Total costs', 'Per attempt', 'Per success', 'Human + rework min', 'Median elapsed s', 'Rework events'],
                          [[a['agent'], str(a['attempts']) + ' / ' + str(a['known_outcomes']), a['success_rate'], totals(a['totals']), totals(a['cost_per_attempt']), totals(a['cost_per_success']) if a['cost_per_success'] else None, a['human_minutes'], a['elapsed_median_seconds'], a['rework_events']] for a in group['agents']]))
    findings = data.get('findings', [])
    if findings:
        body.append('<h2>Suspected inefficiency — review required</h2>')
        body.append(table(['Rule / Task', 'Evidence event : source line', 'Reason', 'Suggested action'],
                          [[f['rule'] + ' / ' + f['task_id'], '; '.join(e['event_id'] + ' : ' + str(e['source_line']) for e in f['evidence']), f['explanation'], f['recommendation']] for f in findings]))
    if data.get('high_cost_steps'):
        body.append('<h2>High-cost steps (per original currency)</h2>')
        body.append(table(['Event', 'Category', 'Amount', 'Currency', 'Origin'], [[c['event_id'], c['category'], c['amount'], c['currency'], c['origin']] for c in data['high_cost_steps']]))
    if data.get('timeline'):
        body.append('<h2>Failure and retry timeline</h2>')
        body.append(table(['Time', 'Event', 'Task', 'Kind', 'Status'], [[e['timestamp'], e['id'], e['task_id'], e['kind'], e.get('status', 'unknown')] for e in data['timeline']]))
    return ''.join(body)


def charts(data):
    """Offline CSS bars, currency-separated; no CDN, scripts, or remote fonts."""
    body = []
    for currency, bucket in data.get("totals", {}).items():
        numbers = {origin: Decimal(value) for origin, value in bucket.items()}
        maximum = max(numbers.values(), default=Decimal(0)) or Decimal(1)
        body.append("<h2>Cost composition · " + html.escape(currency) + "</h2>")
        for origin, value in numbers.items():
            width = min(100, max(0, float(value / maximum * 100)))
            body.append('<p>' + html.escape(origin) + ': ' + html.escape(str(value)) + '</p><div style="height:18px;background:#6ce5bc;width:' + str(width) + '%"></div>')
    trend = data.get("trend", [])
    if trend:
        body.append('<p>Daily chart includes dated event charges. Task-level human allocations are undated and appear in task totals.</p>')
    currencies = sorted({cur for point in trend for cur in point["totals"]})
    for cur in currencies:
        values = [(p["date_utc"], sum((Decimal(v) for v in p["totals"].get(cur, {}).values()), Decimal(0))) for p in trend]
        maximum = max((v for _, v in values), default=Decimal(0)) or Decimal(1)
        body.append("<h2>Daily observed cost · " + html.escape(cur) + " (UTC)</h2>")
        for day, value in values:
            width = min(100, max(0, float(value / maximum * 100)))
            body.append('<p>' + html.escape(day) + ': ' + html.escape(str(value)) + '</p><div style="height:12px;background:#89b4fa;width:' + str(width) + '%"></div>')
    return "".join(body)


def write(data, path, format="json"):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if format == "json":
        atomic_write(target, json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    elif format == "csv":
        stream = io.StringIO(newline="")
        if data.get("report_type") == "comparison":
            fields = ["task_key", "difficulty", "acceptance_id", "variant", "dimension", "attempts", "known_outcomes", "success_rate", "human_minutes", "currency", "origin", "total", "per_attempt", "per_success"]
            rows = []
            for group in data["groups"]:
                for variant in group["agents"]:
                    common = {k: group[k] for k in ("task_key", "difficulty", "acceptance_id")}
                    common.update({k: variant[k] for k in ("dimension", "attempts", "known_outcomes", "success_rate", "human_minutes")})
                    common["variant"] = variant["agent"]
                    if not variant["totals"]:
                        rows.append(common)
                    for cur, bucket in variant["totals"].items():
                        for origin, amount in bucket.items():
                            rows.append(dict(common, currency=cur, origin=origin, total=amount,
                                             per_attempt=variant["cost_per_attempt"][cur][origin],
                                             per_success=variant["cost_per_success"][cur][origin] if variant["cost_per_success"] else ""))
        else:
            fields = ["task_id", "event_id", "category", "amount", "currency", "origin", "price_id"]
            rows = data.get("charges", [])
        writer = csv.DictWriter(stream, fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: "'" + str(v) if str(v).lstrip().startswith(("=", "+", "-", "@")) else v for k, v in row.items() if k in fields})
        atomic_write(target, stream.getvalue())
    elif format == "markdown":
        marker = "SYNTHETIC" if data.get("synthetic") else "OBSERVED / USER-SUPPLIED"
        sections = [f"# AgentWaste — {marker}", "Amounts retain currency and origin. Unknown costs are not zero. Findings are reviewable suspicions."]
        sections.append(markdown_summary(data))
        for key in ("totals", "coverage", "analysis_settings", "tasks", "findings", "high_cost_steps", "trend", "timeline", "groups", "excluded"):
            if key in data:
                # HTML escape untrusted strings and neutralize markdown backtick fences.
                body = html.escape(json.dumps(data[key], indent=2, ensure_ascii=False)).replace("`", "&#96;")
                sections.append('<details><summary>Structured evidence: ' + key.replace('_', ' ').title() + '</summary>\n\n<pre>' + body + '</pre>\n</details>')
        atomic_write(target, "\n\n".join(sections) + "\n")
    elif format == "html":
        title = "AgentWaste — " + ("SYNTHETIC" if data.get("synthetic") else "Audit")
        body = ["<h1>" + title + "</h1><p>Find the Hidden Cost of AI Work.</p>",
                "<p>Currency and provenance stay separate. Unknown is not zero. Heuristics require review. Duration is not automatically labor cost.</p>"]
        if data.get('report_type') == 'audit':
            body.append(table(['Tasks', 'Observed events', 'Accepted successes', 'Unknown cost items', 'Review findings'],
                              [[len(data['tasks']), data['coverage']['events'], data['successful_tasks'], data['coverage']['unknown_cost_items'], len(data['findings'])]]))
        body.append(charts(data))
        body.append(readable(data))
        for key in ("totals", "coverage", "analysis_settings", "tasks", "findings", "high_cost_steps", "trend", "timeline", "groups", "excluded"):
            if key in data:
                body.append("<details><summary>Structured evidence: " + key.replace("_", " ").title() + "</summary><pre>" + html.escape(json.dumps(data[key], indent=2, ensure_ascii=False)) + "</pre></details>")
        document = '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'"><title>' + title + '</title><style>body{font:16px system-ui;max-width:1100px;margin:40px auto;padding:0 20px;background:#101827;color:#e6edf3}h1{color:#6ce5bc}summary{cursor:pointer;font-weight:bold;padding:16px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere;border:1px solid #3b4c60;padding:18px;border-radius:8px}p{line-height:1.6}</style></head><body>' + "".join(body) + "</body></html>"
        atomic_write(target, document)
    else:
        raise ValueError("unsupported report format")
