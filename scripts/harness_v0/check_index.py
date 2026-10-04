"""Verify publishable Git blobs (not just local files), then clean-export replay."""
import argparse
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import tempfile

from .prepare import dump, git, sha
from .runner import PACKAGE, REPO


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-env", type=Path, required=True)
    args = parser.parse_args()
    from dotenv import dotenv_values
    values = [v for k, v in dotenv_values(args.private_env).items() if v and len(v) >= 12 and re.search(r"KEY|TOKEN|SECRET|PASSWORD", k)]
    names = git(REPO, "diff", "--cached", "--name-only").decode().splitlines()
    allowed = {"docs/plans/README.md", "docs/CONTRIBUTIONS.md", "scripts/model_cert.py"}
    checks = []
    for name in names:
        assert name in allowed or name.startswith(("docs/assessments/harness-v0/", "scripts/harness_v0/")), name
        blob = git(REPO, "show", ":" + name)
        assert len(blob) < 50 * 1024 * 1024
        assert not any(v.encode("utf-8") in blob for v in values), "Staged secret found; content withheld"
        assert blob == (REPO / name).read_bytes(), "Git newline conversion would break evidence: " + name
        checks.append({"path": name, "bytes": len(blob), "sha256": sha(blob)})
    tree = git(REPO, "write-tree").decode().strip()
    archive = git(REPO, "archive", tree, "scripts/model_cert.py", "scripts/harness_v0", "docs/assessments/harness-v0")
    with tempfile.TemporaryDirectory(prefix="harness-index-replay-") as temporary:
        root = Path(temporary)
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            for item in tar.getmembers():
                if item.isfile():
                    target = root / item.name
                    assert target.resolve().is_relative_to(root.resolve())
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(tar.extractfile(item).read())
        proc = subprocess.run([sys.executable, "scripts/model_cert.py", "--harness-v0", "replay"], cwd=root,
                              capture_output=True, text=True, encoding="utf-8", timeout=30)
        assert proc.returncode == 0, proc.stderr.replace(temporary, "{TEMP}")
    dump(PACKAGE / "evidence/index-replay.json", {"status": "PASS", "scope": "staged candidate before this self-report",
         "frozen_files_and_evidence_bytes_preserved": True, "staged_files_checked": len(checks),
         "staged_total_bytes": sum(c["bytes"] for c in checks), "index_tree_before_self_report": tree,
         "secret_values_compared": len(values), "clean_export_replay_stdout": proc.stdout,
         "real_model_http_calls": 0})
    print("INDEX_BLOBS_AND_CLEAN_EXPORT_REPLAY_PASS", len(checks))


if __name__ == "__main__":
    main()
