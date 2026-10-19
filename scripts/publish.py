"""Guarded GitHub publication after review. Requires an authenticated gh CLI.

Default is a local plan only. --execute is intended for an already-authorized
maintainer; it creates a PUBLIC repository if absent, pushes, gates on tests.yml
for the exact commit, then publishes v0.1.0 with the verified release assets.
No credential material is read or printed by this script.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="Exact owner/agent-waste-auditor")
    parser.add_argument("--gh", default="gh", help="GitHub CLI executable")
    parser.add_argument("--execute", action="store_true", help="Actually publish; prior maintainer authorization required")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9-]+/agent-waste-auditor", args.repo):
        parser.error("exact owner/agent-waste-auditor required")
    git = ["git", "-c", "safe.directory=" + ROOT.as_posix()]
    def run(command, **kw):
        return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", **kw)
    head = run([*git, "rev-parse", "HEAD"], check=True).stdout.strip()
    if run([*git, "status", "--porcelain"], check=True).stdout.strip():
        raise RuntimeError("working tree must be reviewed and clean")
    assets = []
    for line in (OUT / "SHA256SUMS.txt").read_text().splitlines():
        digest, relative = line.split("  ", 1)
        path = (OUT / relative).resolve()
        if not path.is_relative_to(OUT.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise RuntimeError("release asset checksum mismatch")
        assets.append(path)
    if len(assets) != 3:
        raise RuntimeError("expected source ZIP, wheel and sdist")
    with zipfile.ZipFile(OUT / "agent-waste-auditor-v0.1.0.zip") as archive:
        if archive.comment.decode() != head or archive.testzip() is not None:
            raise RuntimeError("source ZIP does not match the exact reviewed commit")
    plan = {"repo": args.repo, "public": True, "commit": head, "tag": "v0.1.0", "ci_gate": "tests.yml: all jobs for exact commit",
            "assets": [p.name for p in assets], "execute": args.execute}
    print(json.dumps(plan, indent=2), flush=True)
    if not args.execute:
        return
    run([sys.executable, str(ROOT / "scripts/verify_release.py")], check=True)
    gh = shutil.which(args.gh)
    if not gh:
        raise RuntimeError("GitHub CLI not installed")
    login = run([gh, "api", "user", "--jq", ".login"], check=True).stdout.strip()
    if login.casefold() != args.repo.split('/')[0].casefold():
        raise RuntimeError("authenticated user must match explicitly selected repository owner")
    remote = run([gh, "repo", "view", args.repo, "--json", "nameWithOwner,isPrivate"])
    if remote.returncode:
        # Creation still uses GitHub's own collision/access checks; no repository is overwritten.
        run([gh, "repo", "create", args.repo, "--public", "--description", "Find the Hidden Cost of AI Work. Offline AI task economics audit CLI + Skill."], check=True)
    else:
        info = json.loads(remote.stdout)
        if info["isPrivate"]:
            raise RuntimeError("selected repository is private; refusing to change its visibility")
    url = f"https://github.com/{args.repo}.git"
    current = run([*git, "remote", "get-url", "origin"])
    if current.returncode:
        run([*git, "remote", "add", "origin", url], check=True)
    elif current.stdout.strip() != url:
        raise RuntimeError("origin differs from the reviewed target; refusing to replace it")
    helper = "!" + shlex.quote(Path(gh).as_posix()) + " auth git-credential"
    push = [*git, "-c", "credential.helper=", "-c", "credential.helper=" + helper]
    run([*push, "push", "origin", "HEAD:refs/heads/main"], check=True)
    run_id = None
    for _ in range(20):
        p = run([gh, "run", "list", "--repo", args.repo, "--workflow", "tests.yml", "--commit", head, "--limit", "1", "--json", "databaseId"])
        if p.returncode == 0 and json.loads(p.stdout):
            run_id = json.loads(p.stdout)[0]["databaseId"]
            break
        time.sleep(3)
    if run_id is None:
        raise RuntimeError("CI run did not appear; release remains unpublished")
    print(f"Waiting for required tests workflow {run_id} on {head}", flush=True)
    previous = None
    for _ in range(60):
        run_data = json.loads(run([gh, "run", "view", str(run_id), "--repo", args.repo, "--json", "headSha,status,conclusion,jobs,url"], check=True).stdout)
        progress = (run_data['status'], sum(j['conclusion'] == 'success' for j in run_data['jobs']), sum(j['conclusion'] in {'failure', 'cancelled', 'timed_out'} for j in run_data['jobs']))
        if progress != previous:
            print(f"CI {progress[0]}: {progress[1]}/12 passed, {progress[2]} failed/cancelled", flush=True)
            previous = progress
        if run_data['status'] == 'completed':
            break
        time.sleep(15)
    else:
        raise RuntimeError("CI still pending after 15 minutes; release remains unpublished")
    if run_data["headSha"] != head or run_data["conclusion"] != "success" or len(run_data["jobs"]) != 12 or any(j["conclusion"] != "success" for j in run_data["jobs"]):
        raise RuntimeError("exact-commit 12-job CI gate not satisfied")
    existing_tag = run([*git, "rev-parse", "--verify", "refs/tags/v0.1.0^{}"])
    if existing_tag.returncode == 0 and existing_tag.stdout.strip() != head:
        raise RuntimeError("existing local tag points elsewhere; refusing to replace it")
    if existing_tag.returncode:
        run([*git, "-c", "user.name=AgentWaste Development", "-c", "user.email=agentwaste@example.invalid", "tag", "-a", "v0.1.0", "-m", "AgentWaste v0.1.0", head], check=True)
    run([*push, "push", "origin", "refs/tags/v0.1.0"], check=True)
    attachments = [*assets, OUT / "SHA256SUMS.txt", ROOT / "docs/validation-results.json", ROOT / "docs/installation-evidence.json"]
    run([gh, "release", "create", "v0.1.0", *map(str, attachments), "--repo", args.repo, "--verify-tag", "--title", "AgentWaste v0.1.0", "--notes-file", str(ROOT / "docs/RELEASE_NOTES.md")], check=True)
    published = json.loads(run([gh, "release", "view", "v0.1.0", "--repo", args.repo, "--json", "url,isDraft,assets,tagName"], check=True).stdout)
    if published["isDraft"] or len(published["assets"]) != len(attachments):
        raise RuntimeError("release verification failed")
    (OUT / "github-publication.json").write_text(json.dumps({"commit": head, "repo": args.repo, "ci": run_data, "release": published}, indent=2) + "\n", encoding="utf-8")
    print(published["url"], flush=True)


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as exc:
        print("Publication stopped safely: " + str(exc), file=sys.stderr)
        raise SystemExit(1)
    except (ValueError, OSError, KeyError, RuntimeError, subprocess.CalledProcessError):
        print("Publication stopped safely; inspect authentication, repository target, checksums and exact-commit CI before retrying. No force push or tag replacement is performed.", file=sys.stderr)
        raise SystemExit(1)
