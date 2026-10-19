"""Verify source ZIP, wheel, sdist, schemas, evidence and exact-commit identity."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent
sys.path.insert(0, str(ROOT))
from agentwaste.importers.base import load
from agentwaste.schemas import validate_report, validate, SCHEMAS


def main():
    git = ["git", "-c", "safe.directory=" + ROOT.as_posix()]
    head = subprocess.run([*git, "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    status = subprocess.run([*git, "status", "--porcelain"], cwd=ROOT, check=True, capture_output=True, text=True).stdout
    if status.strip():
        raise RuntimeError("working tree must be reviewed and clean")
    members = subprocess.run([*git, "ls-files", "-z"], cwd=ROOT, check=True, capture_output=True).stdout.decode().split('\0')
    members = sorted(n for n in members if n)
    source_zip = OUT / "agent-waste-auditor-v0.1.0.zip"
    with zipfile.ZipFile(source_zip) as z:
        if z.testzip() is not None or z.comment.decode() != head:
            raise RuntimeError("source ZIP CRC or commit identity mismatch")
        names = {n.removeprefix("agent-waste-auditor/") for n in z.namelist() if not n.endswith('/')}
        if names != set(members):
            raise RuntimeError("source ZIP membership differs from Git")
        with zipfile.ZipFile(ROOT / "dist/agent_waste_auditor-0.1.0-py3-none-any.whl") as wheel:
            for path in (n for n in members if n.startswith('agentwaste/') and n.endswith('.py')):
                if wheel.read(path) != z.read('agent-waste-auditor/' + path):
                    raise RuntimeError("wheel code differs from committed source")
        with tarfile.open(ROOT / "dist/agent_waste_auditor-0.1.0.tar.gz") as sdist:
            for path in (n for n in members if n.startswith(('agentwaste/', 'schemas/', 'scripts/', 'docs/')) or n in {'README.md', 'README.zh-CN.md', 'SKILL.md', 'LICENSE', 'pyproject.toml'}):
                archived = sdist.extractfile('agent_waste_auditor-0.1.0/' + path)
                if archived is None or archived.read() != z.read('agent-waste-auditor/' + path):
                    raise RuntimeError("sdist differs from committed source")
    for line in (OUT / "SHA256SUMS.txt").read_text().splitlines():
        digest, name = line.split('  ', 1)
        path = (OUT / name).resolve()
        if not path.is_relative_to(OUT.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise RuntimeError("release checksum mismatch")
    checked = 0
    for path in sorted((ROOT / 'examples/reports').glob('*.json')):
        value = load(path)
        if isinstance(value, dict) and value.get('report_type'):
            validate_report(value)
            checked += 1
        elif isinstance(value, dict) and 'events' in value:
            validate(value, SCHEMAS['dataset'])
            checked += 1
    tests = load(ROOT / 'docs/validation-results.json')
    if tests['failures'] or tests['errors'] or tests['skipped'] or tests['passed'] != tests['tests']:
        raise RuntimeError("local tests not completely passing")
    cli = load(ROOT / 'examples/reports/cli-evidence.json')
    installed = load(ROOT / 'docs/installation-evidence.json')
    if any(c['exit_code'] for c in cli + installed['results']) or not installed['isolated_target_import']:
        raise RuntimeError("CLI or installed artifact evidence failed")
    result = {'git_commit': head, 'working_tree_clean': True, 'zip_source_members_verified': len(members),
              'zip_crc_valid': True, 'zip_exact_commit': True, 'wheel_code_matches_commit': True, 'sdist_matches_commit': True,
              'sha256_verified': True, 'structured_demo_files_validated': checked, 'tests': tests,
              'demo_cli_invocations_passed': len(cli), 'installed_console_checks_passed': installed['passed_commands'],
              'github_matrix_executed': False, 'github_pushed': False}
    (OUT / 'release-verification.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
