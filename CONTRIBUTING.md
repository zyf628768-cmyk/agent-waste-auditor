# Contributing

Use Python 3.11+ and install `python -m pip install '.[test]' build` in a virtual environment. Run `python -m unittest discover -s tests -v`, `python scripts/demo.py` and `python -m build` before proposing a change. Generated schemas and fixtures can be rebuilt with `scripts/generate_schemas.py` and `scripts/generate_fixtures.py`.

New adapters need an explicit structural profile, source-version handling, unknown-field behavior, provenance and cache semantics. Supply minimal SYNTHETIC fixtures and tests for duplicate usage, malformed inputs, redaction and no raw log execution. Never attach private transcripts, credentials or production data to issues or pull requests. Test financial invariants with Decimal and do not silently add currencies, assume prices or infer human wages from duration.

Submit a focused pull request describing the user-visible behavior, assumptions, tests actually executed and limitations. CI must run the configured operating-system/Python matrix before release. Security issues follow SECURITY.md.
