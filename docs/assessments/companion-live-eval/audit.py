"""Offline consistency checks and readable transcripts. No network or production dependencies."""
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVIDENCE = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else HERE
def load(name):
    directory = HERE if name in {"versions.json", "scenes.json"} else EVIDENCE
    return json.loads((directory / name).read_text(encoding="utf-8"))

def lines(name):
    return [json.loads(s) for s in (EVIDENCE / name).read_text(encoding="utf-8").splitlines()]

def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()

def fmt(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def section(doc, title, value):
    doc.extend([title, "", "~~~~", value, "~~~~", ""])

def main():
    turns = lines("dialogues.jsonl")
    wire = lines("requests.jsonl")
    widgets = {a["id"]: a["bubbles"] for a in load("ui_text.json")}
    before = {row["n"]: row for row in wire if row["phase"] == "request"}
    after = {row["n"]: row for row in wire if row["phase"] == "result"}
    assert 0 < len(before) <= 60 and len(wire) == 2 * len(before)
    assert set(before) == set(after) == set(range(1, len(before)+1))
    by_turn = defaultdict(list)
    totals = Counter()
    config = Counter()
    all_turns = {t["id"]:t for t in turns}
    assert len(turns) == len(all_turns) and set(all_turns) == set(widgets)
    scenes = load("scenes.json")
    prompt = (HERE.parent / "companion-v1.2/SYSTEM_PROMPT.txt").read_text(encoding="utf-8").removesuffix("\n")
    assert digest(prompt) == load("versions.json")["candidate_disk"]["disk_active_prompt_sha256"]
    for n, req in before.items():
        res = after[n]
        assert req["turn"] == res["turn"] and req["turn"] in all_turns
        body = req["body"]
        assert req["body_sha256"] == digest(fmt(body))
        assert body["messages"][0]["content"].startswith(prompt + "\n\n")
        assert body["model"] == "deepseek-flash" and body["thinking"] == {"type":"disabled"}
        config[fmt({k:v for k,v in body.items() if k != "messages"})] += 1
        if "error" not in res:
            assert res["model"] == body["model"] and res["choices"] and isinstance(res["usage"]["total_tokens"], int)
            totals.update({k:v for k,v in res["usage"].items() if type(v) == int})
            for choice in res["choices"]:
                assert set(choice["message"]) <= {"role","content","refusal","tool_calls"}
        by_turn[req["turn"]].append(n)
    assert len(config) == 1
    for group, script in scenes.items():
        members = [all_turns[f"{group}-{i}"] for i in range(1,len(script)+1)]
        assert [m["user"] for m in members] == script
        for old, new in zip(members, members[1:]):
            assert new["history_before"][:-2] == old["history_before"]
    doc = ["# 完整合成对话与真实展示文字", "",
           "按采集顺序保留失败、补答和复测。请求编号对应 requests.jsonl 的完整消息及工具 schema。DS 可见输出逐字保留，包括 JSON 转义。解析后的 reply 和 Godot 气泡正文分列。完整解析字段、上下文状态、事件见 dialogues.jsonl。", ""]
    groups = defaultdict(Counter)
    matched = []
    for t in turns:
        tid = t["id"]
        g = tid.rsplit("-",1)[0]
        nums = by_turn[tid]
        counts = groups[g]
        counts["user_turns"] += 1
        counts["wire_attempts"] += len(nums)
        counts["followups_after_first_attempt"] += max(0, len(nums)-1)
        counts["visible_responses"] += sum("choices" in after[n] for n in nums)
        counts["transport_failures"] += sum("error" in after[n] for n in nums)
        events = t["events"]
        counts["rejected_decisions"] += sum(e["kind"]=="task.decision" and not e["payload"]["accepted"] for e in events)
        source = next(e["payload"]["source"] for e in events if e["kind"]=="chat.delivery")
        counts["delivery_"+source] += 1
        if not nums:
            assert source == "memory_correction"
        assert not t["error"] and not t["external_tool_guard"]
        assert sum(e["kind"]=="provider.transport" for e in events) == len(nums)
        assert all(not e["payload"].get("actions") for e in events if e["kind"]=="chat.delivery")
        if t["matched_to"]:
            old = all_turns[t["matched_to"]]
            assert (t["user"],t["history_before"],t["facts_before"]) == (old["user"],old["history_before"],old["facts_before"])
            assert before[nums[0]]["body_sha256"] == before[by_turn[old["id"]][0]]["body_sha256"]
            matched.append(tid)
        doc.extend(["## "+tid, "", "用户", "", t["user"], ""])
        for n in nums:
            res = after[n]
            if "error" in res:
                doc.extend([f"请求 {n} 无可见模型回复。传输异常 {res['error']}。", ""])
            else:
                for c in res["choices"]:
                    msg = c["message"]
                    section(doc, f"请求 {n}，DS 原始可见 content", msg.get("content") or "")
                    if msg.get("tool_calls"):
                        section(doc, "DS 工具调用", fmt(msg["tool_calls"]))
        if not nums:
            doc.extend(["本轮由宿主直接处理，无 DS 请求。", ""])
        for p in t["parsed"]:
            section(doc, "宿主 parse_reply 后的 reply", p["parsed"]["reply"])
        if not t["parsed"]:
            doc.extend(["本轮未经过 parse_reply。", ""])
        bubbles = widgets[tid]
        ui_events = [e for e in t["delivery_events"] if e["type"] in {"core.error","chat.response"}]
        assert len(ui_events) == len(bubbles) and bubbles[-1]["text"] == t["chat_text"].strip()
        for event, bubble in zip(ui_events,bubbles):
            assert event["type"] == bubble["type"] and event.get("text",event.get("message")).strip() == bubble["text"]
            section(doc, "Godot 系统气泡" if bubble["type"]=="core.error" else "Godot 天依气泡", bubble["text"])
        doc.extend(["交付来源 "+source+"。", ""])
    assert len(matched) == 8
    totals_groups = sum(groups.values(), Counter())
    stats = {"groups":groups,"all":totals_groups,"usage_from_successful_responses":totals,"matched_turns":matched,
             "summed_provider_seconds":round(sum(r["seconds"] for r in after.values()),3),
             "summed_handle_chat_seconds":round(sum(t["seconds"] for t in turns),3),
             "widget_bubbles":sum(map(len,widgets.values())), "wire_config_sha256_excluding_messages":digest(next(iter(config))),
             "tool_call_count":sum(len(c["message"].get("tool_calls") or []) for r in after.values() for c in r.get("choices",[]))}
    (EVIDENCE / "DIALOGUES.md").write_text("\n".join(doc), encoding="utf-8", newline="\n")
    (EVIDENCE / "summary.json").write_text(json.dumps(stats,ensure_ascii=False,indent=2)+"\n",encoding="utf-8",newline="\n")
    print(json.dumps({k:v for k,v in stats.items() if k != "groups"},ensure_ascii=False))

if __name__ == "__main__":
    main()
