# Security and privacy

AgentWaste 0.1.x processes only explicit input paths locally. It does not enumerate session directories, read secret environment variables, contact a provider, upload logs or execute log instructions/commands. The CLI is not a production-system operator. Originals are read-only. Use different output paths: existing report files may be replaced.

Import uses field allowlists, drops prompt/message/command/output bodies, hashes redacted argument representations and scrubs common credential/email patterns from labels. Do not place private content in identifiers. Redaction is best effort, not a guarantee against all PII/secret encodings. Stable SHA-256 fingerprints are not anonymization: low-entropy values may be guessed. Keep raw logs, canonical datasets and reports private and review them before sharing. The JSON report renderer expects a generated AgentWaste report; do not use it as a sanitizer for arbitrary JSON.

HTML escapes values and uses a restrictive CSP without scripts or external assets; CSV prefixes formula-leading strings. Inputs are capped at 100 MB. Parsing malformed or deeply nested inputs may still consume resources; process untrusted files in an OS sandbox with appropriate resource limits. Python must be patched and supported. Symlink/hardlink aliases and concurrent source changes are not a hardened hostile-filesystem boundary; use a dedicated output folder and trusted local storage.

Prices and input charges are user/provider claims, not independently certified facts. Native layouts can change without notice; unsupported or incomplete data must be reviewed. Never use missing values as evidence of zero spend.

For a sensitive vulnerability, use GitHub private vulnerability reporting after the repository owner enables it. Do not open a public issue with secrets; if private reporting is unavailable, request a private maintainer contact without including exploit details. No unconfigured security mailbox is advertised. Security fixes target the current 0.1.x release; no formal response SLA is promised.
