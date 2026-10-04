"""Codex: safe pre-push checks, including a clean Git-index export replay."""
import argparse
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import tempfile

from .gateway_probe import BATCH
from .prepare import dump, git, sha
from .runner import PACKAGE, REPO


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--private-env", type=Path, required=True)
    args = p.parse_args()
    from dotenv import dotenv_values
    secrets = [v for k, v in dotenv_values(args.private_env).items() if v and len(v) >= 12 and re.search(r"KEY|TOKEN|SECRET|PASSWORD", k)]
    baseline = json.loads((PACKAGE / "evidence/baseline/manifest.json").read_text(encoding="utf-8"))
    source_equal = all(sha((args.source / name).read_text(encoding="utf-8")) == digest for name, digest in baseline["files"].items())
    names = git(REPO, "diff", "--cached", "--name-only").decode().splitlines()
    assert names, "Stage only this candidate supplement before checking"
    for name in names:
        assert name in {"docs/plans/README.md", "docs/CONTRIBUTIONS.md", "docs/assessments/harness-v0/REPORT.md"} or name.startswith(("docs/assessments/harness-v0/batches/gateway-resume-01/", "scripts/harness_v0/")), name
        blob = git(REPO, "show", ":" + name)
        assert blob == (REPO / name).read_bytes(), "Index newline mismatch: " + name
        assert len(blob) < 50 * 1024 * 1024
        assert not any(secret.encode() in blob for secret in secrets), "Secret detected; withheld"
    checks = []
    with tempfile.TemporaryDirectory(prefix="harness-resume-release-") as temporary:
        root = Path(temporary)
        env = os.environ.copy()
        for k in list(env):
            if k.startswith(("ANIME_AGENT_", "GLM_", "DEEPSEEK_", "LLM_", "STEPFUN_", "QWEN_")):
                del env[k]
        env.update(ANIME_AGENT_CONFIG_PATH=str(root / "no-config.env"), ANIME_AGENT_DATA_DIR=str(root / "data"),
                   LLM_PROVIDER="mock", ANIME_AGENT_TTS="0", ANIME_AGENT_MCP_SERVERS="", ANIME_AGENT_WAKE_WORD="0", PYTHONUTF8="1")
        for command in ([sys.executable, "scripts/check_docs_consistency.py"], ["git", "diff", "--check"], ["git", "diff", "--cached", "--check"]):
            proc = subprocess.run(command, cwd=REPO, env=env, capture_output=True, text=True, encoding="utf-8", timeout=60)
            text = (proc.stdout + proc.stderr).replace(str(REPO), "{REPO}").replace(REPO.as_posix(), "{REPO}").replace(temporary, "{TEMP}")
            checks.append({"command": ["python" if a == sys.executable else a for a in command], "exit_code": proc.returncode, "output": text})
            assert proc.returncode == 0, "Offline delivery check failed"
        tree = git(REPO, "write-tree").decode().strip()
        archive = git(REPO, "archive", tree, "scripts/model_cert.py", "scripts/harness_v0", "docs/assessments/harness-v0")
        clean = root / "clean-export"
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            for item in tar.getmembers():
                if item.isfile():
                    target = clean / item.name
                    assert target.resolve().is_relative_to(clean.resolve())
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(tar.extractfile(item).read())
        for command in ([sys.executable, "scripts/model_cert.py", "--harness-v0", "replay"],
                        [sys.executable, "-m", "scripts.harness_v0.resume_batch", "replay"]):
            proc = subprocess.run(command, cwd=clean, env=env, capture_output=True, text=True, encoding="utf-8", timeout=60)
            assert proc.returncode == 0, "Clean-index replay failed: " + proc.stderr.replace(temporary, "{TEMP}")
            checks.append({"command": ["python" if a == sys.executable else a for a in command], "clean_index_export": True,
                           "exit_code": proc.returncode, "output": proc.stdout})
    dump(BATCH / "delivery-checks.json", {"status": "PASS", "production_core_contacted": False,
         "production_source_matches_original_manifest": source_equal, "candidate_prompt_active": False,
         "real_http_calls": 0, "secret_values_compared": len(secrets), "staged_file_count": len(names),
         "index_tree_before_this_self_report": tree, "checks": checks,
         "independent_agent_whitepaper_gate": "not run; Manager acceptance pending"})
    print("CANDIDATE_SUPPLEMENT_CHECKS_PASS", len(names), "files; production source matches", source_equal)


if __name__ == "__main__":
    main()
