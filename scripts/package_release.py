"""Package public source files only; never recursively include a workspace."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent


def main():
    git = ["git", "-c", "safe.directory=" + ROOT.as_posix()]
    state = subprocess.run([*git, "status", "--porcelain"], cwd=ROOT, check=True, capture_output=True)
    if state.stdout.strip():
        raise RuntimeError("commit/review source and validation evidence before packaging; working tree must be clean")
    # Git-tracked membership prevents accidental inclusion of unrelated private files.
    p = subprocess.run([*git, "ls-files", "-z"], cwd=ROOT, check=True, capture_output=True)
    names = sorted(n for n in p.stdout.decode("utf-8").split("\0") if n)
    if not names:
        raise RuntimeError("commit public source files before packaging")
    target = OUT / "agent-waste-auditor-v0.1.0.zip"
    for name in names:
        source = ROOT / name
        if not source.resolve().is_relative_to(ROOT.resolve()) or not source.is_file() or source.is_symlink():
            raise RuntimeError("unsafe source member")
    # Archive committed blobs instead of worktree line endings or generated extras.
    subprocess.run([*git, "archive", "--format=zip", "--prefix=agent-waste-auditor/", "--output=" + str(target), "HEAD"], cwd=ROOT, check=True)
    with zipfile.ZipFile(target) as z:
        if z.testzip() is not None:
            raise RuntimeError("ZIP CRC failed")
    files = [target, *sorted((ROOT / "dist").glob("*"))]
    hashes = [hashlib.sha256(f.read_bytes()).hexdigest() + "  " + (f.name if f.parent == OUT else "agent-waste-auditor/dist/" + f.name) for f in files if f.is_file()]
    (OUT / "SHA256SUMS.txt").write_text("\n".join(hashes) + "\n", encoding="utf-8")
    print(json.dumps({"zip": str(target), "tracked_members": len(names), "assets": [str(f) for f in files]}, indent=2))


if __name__ == "__main__":
    main()
