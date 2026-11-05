"""Validate with the unmodified official checker and build an immutable ZIP."""
import argparse
import hashlib
import io
import json
import re
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "skill/vaultmind-ai"


def package(node="node", version="0.1.1"):
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("Use a numeric semantic version")
    checker = ROOT / "vendor/official/uliya-skill-kit/scripts/check-skill.mjs"
    result = subprocess.run([node, str(checker), str(SOURCE)], capture_output=True, text=True, encoding="utf-8", check=True)
    report = json.loads(result.stdout)
    if report["status"] != "static-pass" or report["summary"]["warnings"]:
        raise ValueError("Official checker must pass without warnings")
    files = sorted(p for p in SOURCE.rglob("*") if p.is_file())
    if any(p.is_symlink() for p in SOURCE.rglob("*")):
        raise ValueError("Links are not allowed")
    names = [p.relative_to(SOURCE).as_posix() for p in files]
    if any(n != "SKILL.md" and not re.fullmatch(r"references/[a-z0-9-]+\.md", n) for n in names):
        raise ValueError("Non-Markdown or unexpected package file")
    assert "SKILL.md" in names and len(files) <= 100
    blobs = {name: path.read_bytes() for name, path in zip(names, files)}
    assert all(len(blob) < 1_000_000 for blob in blobs.values())
    assert sum(map(len, blobs.values())) < 10_000_000
    recorded = {entry["path"]: entry["sha256"] for entry in report["files"]}
    assert recorded == {name: hashlib.sha256(blob).hexdigest() for name, blob in blobs.items()}
    memory = io.BytesIO()
    with zipfile.ZipFile(memory, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, blob in blobs.items():
            entry = zipfile.ZipInfo(name, (2026, 10, 28, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, blob)
    payload = memory.getvalue()
    assert len(payload) < 10_000_000
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        assert archive.testzip() is None
        assert all(archive.read(name) == blob for name, blob in blobs.items())
    output = ROOT / f"releases/vaultmind-ai-{version}-pretest.zip"
    output.parent.mkdir(exist_ok=True)
    if output.exists():
        if output.read_bytes() != payload:
            raise ValueError("Release exists with different content; increment the version")
    else:
        with output.open("xb") as stream:
            stream.write(payload)
    release = {"version": version, "zip": output.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(payload).hexdigest(), "zip_bytes": len(payload), "uncompressed_bytes": sum(map(len, blobs.values())), "file_count": len(files), "entries": names, "static_status": report["status"], "nas_validation": "not performed"}
    (ROOT / "artifacts/official-check.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (ROOT / "artifacts/release.json").write_text(json.dumps(release, indent=2), encoding="utf-8")
    print(json.dumps(release, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--node", default="node")
    parser.add_argument("--version", default="0.1.1")
    args = parser.parse_args()
    package(args.node, args.version)
