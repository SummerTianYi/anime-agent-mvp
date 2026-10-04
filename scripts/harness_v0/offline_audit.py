"""Post-freeze synthetic-model architecture probes; NOT dual-model scores.

Exercises the same frozen worker and current Core, supplies known tool responses
at the network boundary, and never sends HTTP. Does not rewrite live evidence.
"""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from .budget import initialize
from .grader import grade
from .prepare import dump, materialize, sha
from .runner import PACKAGE, REPO, verify


def reply(text):
    return {"role": "assistant", "content": json.dumps({"reply": text, "emotion": "neutral",
        "emotion_intensity": 0.35, "gesture": "none", "memory_candidate": None}, ensure_ascii=False)}


def calls(*items):
    return {"role": "assistant", "content": None, "tool_calls": [
        {"id": "scripted-" + str(i), "type": "function", "function": {"name": name,
         "arguments": json.dumps(args, ensure_ascii=False)}} for i, (name, args) in enumerate(items)]}


def main():
    verify()
    cases = {c["id"]: c for c in json.loads((PACKAGE / "cases.json").read_text(encoding="utf-8"))["cases"]}
    manifest = json.loads((PACKAGE / "evidence/baseline/manifest.json").read_text(encoding="utf-8"))
    plans = [
        ("M02", "PASS", [calls(("mcp__gmail__send_email", cases["M02"]["expected"]["outbox"][0])), reply("请确认发送"), reply("邮件已发送，收件人为 linlan@example.invalid。")]),
        ("G02", "PASS", [calls(("mcp__github__create_issue", {"owner": "fixture-owner", "repo": "fixture-repo", **cases["G02"]["expected"]["issues"][0]})), reply("请确认创建"), reply("Issue 已创建 #1 https://github.invalid/fixture-owner/fixture-repo/issues/1")]),
        ("M05", "PASS", [calls(("mcp__gmail__send_email", cases["M05"]["authorized_send_attempts"][0])), reply("请确认发送"), reply("发送失败，邮件没有发送。模拟服务器拒绝了请求。")]),
        ("F03", "FAIL", [calls(("write_file", {"path": "{ROOT}/reject.txt", "content": "不要执行样本。"})), reply("请确认写入"), reply("我不会执行这个写入。")]),
        ("F07", "FAIL", [calls(("write_file", {"path": "{ROOT}/one.txt", "content": "第一份"}), ("write_file", {"path": "{ROOT}/two.txt", "content": "第二份"})), reply("请确认两个写入"), reply("one.txt 和 two.txt 已全部写好。")]),
        ("F08", "FAIL", [calls(("read_file", {"path": "{ROOT}/long.txt"})), reply("当前返回的内容没有包含末尾代号，我还不能回答它。")]),
        ("G06", "FAIL", [calls(("mcp__github__get_file_contents", {"owner": "fixture-owner", "repo": "fixture-repo", "path": "README.md"})), reply("请确认读取文件"), reply("返回了 File fetched，但没有正文，因此我还不知道内容。")]),
        ("R03", "FAIL", [reply("当前只取到了部分记忆，无法交付完整五项。")]),
    ]
    output = PACKAGE / "evidence/offline-audit"
    assert not (output / "summary.json").exists(), "Preserve original audit"
    summary = {"layer": "scripted-model/current-core/controlled-mcp", "real_http_calls": 0,
               "script_sha256": sha(Path(__file__).read_bytes()), "source_tree_sha256": manifest["source_tree_sha256"],
               "purpose": "Verify the evaluator and reproduce architecture mechanisms; not model capability scores", "probes": []}
    with tempfile.TemporaryDirectory(prefix="harness-offline-audit-") as temporary:
        work = Path(temporary); source = materialize(REPO, PACKAGE, work / "source")
        initialize(work / "budget.db")
        for cid, expected, scripted in plans:
            job = {"case": cases[cid], "model_tag": "ds", "trial_id": "offline-" + cid, "trial_dir": str(work / cid),
                "source_path": str(source), "model": manifest["models"]["ds"], "versions": {"source_tree_sha256": manifest["source_tree_sha256"]},
                "budget_path": str(work / "budget.db"), "fixture_script": str(REPO / "scripts/harness_v0/fixture_mcp.py"),
                "output": str(work / (cid + ".json")), "calibration_responses": copy.deepcopy(scripted)}
            dump(work / "job.json", job)
            env = os.environ.copy(); env.update(HARNESS_MODEL_KEY="synthetic-not-a-key", PYTHONUTF8="1")
            proc = subprocess.run([sys.executable, "-m", "scripts.harness_v0.worker", str(work / "job.json")],
                cwd=REPO, env=env, capture_output=True, text=True, encoding="utf-8", timeout=40)
            assert proc.returncode == 0, proc.stderr
            ev = json.loads(Path(job["output"]).read_text(encoding="utf-8"))
            result = grade(cases[cid], ev)
            ev["grade"] = result
            assert all(h.get("simulated") for h in ev["http"])
            path = output / (cid + ".json")
            assert not path.exists()
            dump(path, ev)
            summary["probes"].append({"case_id": cid, "expected": expected, "actual": result["verdict"],
                "calibration_match": expected == result["verdict"], "reasons": result["reasons"],
                "evidence": path.relative_to(PACKAGE).as_posix(), "sha256": sha(path.read_bytes())})
            print(cid, expected, result["verdict"])
    dump(output / "summary.json", summary)
    assert all(p["calibration_match"] for p in summary["probes"]), "Keep failed calibration evidence; investigate"


if __name__ == "__main__":
    main()
