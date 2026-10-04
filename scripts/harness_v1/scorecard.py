"""Generate auditable per-model tables; never merge repair results into first scores."""
from collections import Counter
import json
import os
from pathlib import Path
from .package import PACKAGE, ROOT, rows


def main():
    old = ROOT / "docs/assessments/harness-v0"
    regrades = {r["trial_id"]: r["v1_regrade"] for r in json.loads((PACKAGE / "evidence/calibration/v0-regraded.json").read_text(encoding="utf-8"))["rows"]}
    baseline = []
    for directory in (old, old / "batches/gateway-resume-01"):
        for row in rows(directory / "results.jsonl"):
            if not row["attempted"]:
                continue
            path = directory / row["evidence_path"]
            row["evidence_path"] = Path(os.path.relpath(path, PACKAGE)).as_posix()
            baseline.append(row)
    current = rows(PACKAGE / "results.jsonl")
    batches = sorted({r["trial_id"].rsplit("-", 3)[0] for r in current})
    lines = ["# 双模型成绩与逐题索引", "", "自动生成，首批和修复批分列。V0每模型79次包含一次旧429尝试，不等于79个独立题；每模型26题。校准重判不代表运行改进，也不重复计算API。", "",
        "| 批次/口径 | 模型 | 用例数 | 实际运行 | PASS | PARTIAL | FAIL | BLOCKED | HTTP |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    def stat(label, items, tag, calibrated=False):
        selected = [r for r in items if r["model_tag"] == tag]
        counts = Counter(regrades[r["trial_id"]]["verdict"] if calibrated else r["verdict"] for r in selected)
        lines.append("| " + " | ".join(map(str, [label, tag, len({r["case_id"] for r in selected}),
            sum(r["attempted"] for r in selected), *[counts.get(k, 0) for k in ("PASS", "PARTIAL", "FAIL", "BLOCKED")], sum(r["http_calls"] for r in selected)])) + " |")
    for tag in ("ds", "glm"):
        stat("V0 原分", baseline, tag)
        stat("V0 校准离线重判", baseline, tag, True)
    for batch in batches:
        for tag in ("ds", "glm"):
            stat(batch, [r for r in current if r["trial_id"].startswith(batch+"-")], tag)
    accounting = json.loads((PACKAGE / "http-accounting.json").read_text(encoding="utf-8"))
    lines += ["", f"V1 实际HTTP：**{accounting['http_calls']}/{accounting['cap']}**。V0任务HTTP566和两次先前网关探针属于历史基线，不计入V1本轮调用。", "",
              "## 逐题三重复（点击每个结果查看原始脱敏证据）", "",
              "| 题目 | DS V0重判 | GLM V0重判 | "+" | ".join(f"{tag.upper()} {batch}" for batch in batches for tag in ("ds","glm"))+" |",
              "|"+"---|"*(3+2*len(batches))]
    def cells(items, cid, tag, calibrated=False):
        selected = [r for r in items if r["case_id"] == cid and r["model_tag"] == tag]
        return " / ".join(f"[{regrades[r['trial_id']]['verdict'] if calibrated else r['verdict']} r{r['repeat']}]({r['evidence_path']})" for r in selected) or "未在该版本复测"
    for case in json.loads((PACKAGE / "cases.json").read_text(encoding="utf-8"))["cases"]:
        cid = case["id"]
        values = [cid+" "+case["title"], cells(baseline,cid,"ds",True), cells(baseline,cid,"glm",True)]
        for batch in batches:
            subset = [r for r in current if r["trial_id"].startswith(batch+"-")]
            values.extend(cells(subset,cid,tag) for tag in ("ds","glm"))
        lines.append("| "+" | ".join(values)+" |")
    lines += ["", "## V1所有非PASS记录（不删反例）", "", "| 运行 | 结果 | 判分原因 |", "|---|---|---|"]
    for row in current:
        if row["verdict"] != "PASS":
            lines.append(f"| [{row['trial_id']}]({row['evidence_path']}) | {row['verdict']} | {', '.join(row['reasons']) or 'external blocked'} |")
    (PACKAGE / "scorecard.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    print(json.dumps(dict(batches=batches, v1_rows=len(current), historical_actual_runs=len(baseline), http_calls=accounting["http_calls"])))


if __name__ == "__main__":
    main()
