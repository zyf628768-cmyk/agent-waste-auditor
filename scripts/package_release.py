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
    # Git-tracked membership prevents accidental inclusion of unrelated private files.
    p = subprocess.run(["git", "-c", "safe.directory=" + ROOT.as_posix(), "ls-files", "-z"], cwd=ROOT, check=True, capture_output=True)
    names = sorted(n for n in p.stdout.decode("utf-8").split("\0") if n)
    if not names:
        raise RuntimeError("commit public source files before packaging")
    target = OUT / "agent-waste-auditor-v0.1.0.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        for name in names:
            source = ROOT / name
            if not source.resolve().is_relative_to(ROOT.resolve()) or not source.is_file():
                raise RuntimeError("unsafe source member")
            info = zipfile.ZipInfo("agent-waste-auditor/" + name, date_time=(2026, 10, 19, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info, source.read_bytes())
    with zipfile.ZipFile(target) as z:
        if z.testzip() is not None:
            raise RuntimeError("ZIP CRC failed")
    files = [target, *sorted((ROOT / "dist").glob("*"))]
    hashes = [hashlib.sha256(f.read_bytes()).hexdigest() + "  " + (f.name if f.parent == OUT else "agent-waste-auditor/dist/" + f.name) for f in files if f.is_file()]
    (OUT / "SHA256SUMS.txt").write_text("\n".join(hashes) + "\n", encoding="utf-8")
    print(json.dumps({"zip": str(target), "tracked_members": len(names), "assets": [str(f) for f in files]}, indent=2))


if __name__ == "__main__":
    main()
