"""Title-only GitHub update contract. No authorization or tool synthesis."""
from __future__ import annotations

import copy
import json
import re

READ = "mcp__github__issue_read"
WRITE = "mcp__github__issue_write"
TARGET = ("owner", "repo", "issue_number")
PRESERVED = ("body", "state", "state_reason", "labels", "assignees", "milestone", "locked", "active_lock_reason", "type", "issue_type")
GUIDANCE = """【当前 Issue 标题任务的交付条件】
先实际 issue_read(method=get) 读取目标，保留用户字段基线；再 issue_write(method=update)，
参数只允许 method、owner、repo、issue_number、title。标题逐字符合原要求，不能附带正文、状态或标签等修改。
每次工具调用继续经过原权限和必要确认。更新成功后继续原任务，实际重新 issue_read(method=get) 同一 Issue，
不要再次更新，不需要用户另发读取指令。同参数旧读取不代表更新后的读取。
最终 report 引用真实动作/读取，宿主核对本次更新后的标题与保留字段。失败或未知分别交代，不能宣称全部完成。
参数不足请 clarify，不生成口头待办。"""
TITLE_MARKER = r"标题\s*(?:修改为|修改成|更改为|更新为|改为|改成|换成|设置为|设为|为|是|[:：])\s*"


def requested(text):
    # This adapter owns the explicit update-and-reread obligation only.
    # Quoted title/repository data cannot request the extra workflow.
    control_text = re.sub(r'「[^」]*」|“[^”]*”|"[^"\n]*"|`[^`]*`|‘[^’]*’', " ", text)
    control_text = re.sub(r"(?:无需|不用|不要|不必|别)(?:再次|重新|实际)?(?:读取|读回|重读|再读)", "", control_text)
    if not re.search(r"读取|重读|再读|读回", control_text):
        return False
    marker = re.search(TITLE_MARKER, text)
    instruction = text[:marker.end()] if marker else text
    if re.match(r"^\s*[‘’\"“`「]", instruction):
        return False
    if re.match(r"^(?:(?:请|你|能不能|能|可以|可否|帮我|一下|只|我想|了解)\s*)*(?:解释|说明|介绍|讲解|如何|怎么|怎样)", instruction):
        return False
    control = re.sub(r"(?:不要|不必|无需|不用|别)(?:实际)?(?:修改|更新|更改|改)(?:其他|其它)[^，。；\n]*", "", instruction)
    if re.search(r"(?:不要|不必|无需|不用|别)(?:实际)?(?:修改|更新|更改|改)", control):
        return False
    return bool(re.search(r"issue", instruction, re.I) and "标题" in instruction
                and re.search(r"改|更新|换成|设为|设置为", instruction))


def contract(text, previous=None):
    value = dict(previous or {})
    marker = re.search(TITLE_MARKER, text)
    # Title data may itself contain a repository/number. It cannot retarget
    # an edit that only supplies a new title.
    instruction = text[:marker.start()] if marker else text
    repo = re.search(r"(?:https://github\.com/)?\b([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)(?:/issues/(\d+))?", instruction)
    number = re.search(r"(?:Issue\s*#?\s*|#)([1-9]\d*)", instruction, re.I)
    if repo:
        value.update(owner=repo[1], repo=repo[2])
        if repo[3]:
            value["issue_number"] = int(repo[3])
    if number:
        value["issue_number"] = int(number[1])
    if marker:
        literal = text[marker.end():]
        pairs = {"「": "」", "“": "”", '"': '"', "`": "`", "‘": "’"}
        if literal and literal[0] in pairs:
            end = literal.find(pairs[literal[0]], 1)
            if end > 1:
                value["title"] = literal[1:end]
        else:
            title = re.split(r"[，。\n]", literal, maxsplit=1)[0].strip()
            if title:
                value["title"] = title
    return value


def same_target(left, right):
    return all(left.get(k) == right.get(k) and left.get(k) is not None for k in TARGET)


def snapshot(result, target):
    if result.get("ok") is not True:
        return None
    raw = result.get("raw_result", {})
    data = raw.get("structuredContent")
    if not isinstance(data, dict):
        try:
            data = json.loads(result.get("output", ""))
        except (ValueError, TypeError):
            return None
    expected = f"https://github.com/{target.get('owner')}/{target.get('repo')}/issues/{target.get('issue_number')}"
    if (not isinstance(data, dict) or data.get("number") != target.get("issue_number")
            or data.get("html_url") != expected or not isinstance(data.get("title"), str)
            or any(k not in data for k in ("body", "state", "labels"))):
        return None
    return copy.deepcopy({k: data[k] for k in ("title", *PRESERVED) if k in data})


def reads(task, sid, target):
    return [r for r in task.get("tool_results", []) if r.get("session_id") == sid and r.get("task_id") == task["id"]
            and r["tool"] == READ and r["arguments"].get("method") == "get" and same_target(r["arguments"], target)]


def baseline(task, sid, target):
    for record in reversed(reads(task, sid, target)):
        value = snapshot(record["result"], target)
        if value is not None and not record.get("after_actions"):
            return {"snapshot": value, "result_ref": record["result_ref"]}
    return None


def writes(task, sid, actions):
    return [a for a in actions if a["session_id"] == sid and a["task_id"] == task["id"] and a["tool"] == WRITE]


def after_actions(task, sid, actions, name, args):
    if name != READ or args.get("method") != "get":
        return []
    return [a["action_id"] for a in writes(task, sid, actions)
            if a["status"] == "succeeded" and same_target(a["arguments"], args)]


def proposal_error(task, sid, name, args):
    expected = task["issue_contract"]
    if name not in {READ, WRITE, "read_tool_result"}:
        return "本任务只授权目标 Issue 的标题更新与读取核验"
    if name == "read_tool_result":
        return ""
    if any(k not in expected for k in (*TARGET, "title")):
        return "Issue 任务缺少明确仓库、编号或逐字标题；请澄清（标题可用引号标明），不能猜测参数"
    if not same_target(args, expected):
        return "工具目标与用户指定的仓库/Issue 编号不一致"
    allowed = {"method", *TARGET, *(["title"] if name == WRITE else [])}
    if set(args) - allowed or args.get("method") != ("update" if name == WRITE else "get"):
        return "仅允许 issue_write(update) 修改 title，或 issue_read(get)；额外修改字段禁止"
    if name == WRITE:
        if args.get("title") != expected["title"]:
            return "提案标题与用户要求不逐字一致"
        if baseline(task, sid, args) is None:
            return "更新前缺少同一 Issue 的真实读取基线；请先 issue_read(get)，确认后再提出更新"
    return ""


def verified(action, task, sid):
    before = (action.get("verification_before") or {}).get("snapshot")
    if before is None or action["status"] != "succeeded":
        return None
    # The latest actual post-write read controls the verdict; a later
    # mismatch cannot be hidden by selecting an older successful reference.
    candidates = [r for r in reads(task, sid, action["arguments"])
                  if action["action_id"] in r.get("after_actions", [])]
    if not candidates:
        return None
    record = candidates[-1]
    after = snapshot(record["result"], action["arguments"])
    if after == {**before, "title": action["arguments"]["title"]}:
        return record
    return None


def completion_error(task, sid, actions, mode, **_):
    active = [a for a in writes(task, sid, actions) if a["status"] != "cancelled"]
    if not active:
        if mode == "clarify":
            return ""
        return "原 Issue 任务尚缺真实标题更新提案；旧读取或 chat 不能证明更新完成"
    for action in active:
        if action["status"] == "succeeded" and not verified(action, task, sid):
            return "标题更新已执行，禁止重写；仍须实际重新读取同一 Issue，核验逐字标题和其他用户字段不变"
    return ""


def render(task, sid, actions, fallback, **_):
    active = [a for a in writes(task, sid, actions) if a["status"] != "cancelled"]
    if active and all(verified(a, task, sid) for a in active):
        lines = ["Issue 任务已完成：更新成功，已实际重新读取，标题逐字一致且其他用户字段保持不变。"]
        for a in active:
            args = a["arguments"]
            lines.append(f"仓库：{args['owner']}/{args['repo']}，Issue #{args['issue_number']}\n核验后的标题：{args['title']}\n读取记录：{verified(a, task, sid)['result_ref']}")
        return "\n".join(lines)
    if any(a["status"] == "succeeded" for a in active):
        return "Issue 标题更新成功；后置读取核验未通过或尚未取得，任务尚未完成。已保留回执，不会重新写入。\n" + fallback
    # Never display a model's read summary as proof of this mutation.
    if not active and not task.get("blocked"):
        if fallback.startswith("还需要你补充"):
            return fallback
        return "Issue 任务尚未完成：尚无有效标题更新提案。\n" + (fallback if "待确认" in fallback else "未生成更新票据。")
    return fallback + "\nIssue 任务尚未完成：更新及新读取核验尚未全部完成。"
