"""Offline parser-only counterfactual, not a new model score or overwritten trial."""
import json
from pathlib import Path
import sys
import subprocess
from scripts.harness_v0.prepare import dump, sha
ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "docs/assessments/harness-v1"
sys.path.insert(0, str(ROOT / "services/agent-core"))
from agent_core.harness import CharacterHarness
records = []
for path in sorted((PACKAGE / "batches/core-01/evidence").glob("*-P0*.json")):
    ev = json.loads(path.read_text(encoding="utf-8"))
    responses = [h.get("response_body", {}).get("choices", []) for h in ev["http"] if h.get("status") == 200]
    if not responses:
        continue
    raw = responses[-1][0]["message"].get("content") or ""
    original = [e["text"] for e in ev["events"] if e.get("type") == "chat.response"][-1]
    parsed = CharacterHarness.parse_reply(raw).reply
    records.append(dict(trial_id=ev["trial_id"], source_evidence=path.relative_to(PACKAGE).as_posix(),
        source_evidence_sha256=sha(path.read_bytes()), raw_sha256=sha(raw), original_display=original,
        candidate_display=parsed, changed=original != parsed,
        recovered_format_error="这次回复格式出了问题" in original and "这次回复格式出了问题" not in parsed,
        original_grade_unchanged=ev["grade"]["verdict"]))
dump(PACKAGE / "evidence/parser-replay.json", dict(source_sha=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
    parser_file_sha256=sha((ROOT / "services/agent-core/agent_core/harness.py").read_bytes()),
    llm_calls=0, model_trials_not_regraded=True, records=records))
print(json.dumps(dict(records=len(records), changed_displays=sum(r["changed"] for r in records),
                      recovered_format_errors=sum(r["recovered_format_error"] for r in records), llm_calls=0)))
