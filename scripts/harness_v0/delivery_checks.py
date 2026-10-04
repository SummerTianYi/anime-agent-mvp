"""Codex: isolated offline pre-push checks, records only sanitized summaries."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from .prepare import dump, sha
from .runner import PACKAGE, REPO


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--private-env", type=Path, required=True)
    args = parser.parse_args()
    def scrub(text):
        for path, label in ((REPO, "{REPO}"), (args.source, "{SOURCE}")):
            text = text.replace(str(path), label).replace(path.as_posix(), label)
        return text
    previous_path = PACKAGE / "evidence/delivery-checks.json"
    if previous_path.exists():
        previous = json.loads(previous_path.read_text(encoding="utf-8"))
        for record in previous.get("checks", []):
            record["output"] = scrub(record["output"])
        if previous.get("status") != "PASS":
            dump(PACKAGE / "evidence/delivery-check-failed-attempt.json", previous)
        dump(previous_path, previous)
    manifest = json.loads((PACKAGE / "evidence/baseline/manifest.json").read_text(encoding="utf-8"))
    unchanged = all(sha((args.source / name).read_text(encoding="utf-8")) == digest for name, digest in manifest["files"].items())
    assert unchanged, "Production source changed; inspect without overwriting"
    records = []
    with tempfile.TemporaryDirectory(prefix="harness-delivery-check-") as temporary:
        env = os.environ.copy()
        env.update(ANIME_AGENT_CONFIG_PATH=str(Path(temporary) / "no-config.env"), ANIME_AGENT_DATA_DIR=str(Path(temporary) / "data"),
                   LLM_PROVIDER="mock", ANIME_AGENT_TTS="0", ANIME_AGENT_MCP_SERVERS="", ANIME_AGENT_WAKE_WORD="0", PYTHONUTF8="1")
        commands = [
            ([sys.executable, "-m", "scripts.harness_v0.verify_package", "--private-env", str(args.private_env)],
             "python -m scripts.harness_v0.verify_package --private-env <private-test.env>"),
            ([sys.executable, "scripts/check_docs_consistency.py"], "python scripts/check_docs_consistency.py"),
            (["git", "diff", "--check"], "git diff --check"),
            (["git", "diff", "--cached", "--check"], "git diff --cached --check"),
        ]
        for command, display in commands:
            proc = subprocess.run(command, cwd=REPO, env=env, capture_output=True, text=True, encoding="utf-8", timeout=60)
            output = scrub(proc.stdout + proc.stderr).replace(temporary, "{TEMP}")
            records.append({"command": display, "exit_code": proc.returncode, "output": output})
    result = {"status": "PASS" if all(x["exit_code"] == 0 for x in records) else "FAIL",
              "production_source_manifest_unchanged": unchanged, "production_core_contacted": False,
              "real_model_http_calls": 0, "candidate_prompt_activated": False,
              "independent_agent_whitepaper_gate": "not run; Manager acceptance pending", "checks": records}
    dump(PACKAGE / "evidence/delivery-checks.json", result)
    print(result["status"], [(r["command"], r["exit_code"]) for r in records])
    assert result["status"] == "PASS"


if __name__ == "__main__":
    main()
