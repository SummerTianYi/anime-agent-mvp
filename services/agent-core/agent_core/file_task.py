"""A narrow write-then-read obligation, separate from model presentation.

No tool calls or arguments are synthesized here. The model still proposes and
reads through the existing loop; only host receipts can discharge the task.
"""
from __future__ import annotations

import hashlib
import os
import re


FILE_TASK_GUIDANCE = """【当前文件任务的交付条件】
原任务要求写入文件、随后实际调用 read_file 并展示完整内容。
先用 write_file 的真实 tool_calls 提出参数，等用户正常确认。确认成功后继续原任务，
根据真实写入回执的路径调用 read_file；不要再次写入，不要要求用户另外发起读取。
用户以“内容如下：”提供字面正文时，之后的每个字符都属于正文；行首即使看似序号或说明，
也不是可删除的标注。完整保留行首、标点、单位、日期和换行；不要替用户精简正文。
write_file 内部的 verified_readback 只证明写入校验，不能替代 read_file。
最终 report 引用真实动作及读取 result_ref。宿主从实际读回正文交付，不用摘要替代原文。
缺少参数用 clarify；无提案、失败或未知结果均不能宣称任务完成。"""


def requests_file_delivery(text: str) -> bool:
    """Recognize explicit Chinese file write/read requests, not quoted lessons.

    This intentionally is not a general intent classifier. Payload after the
    content delimiter is data and must not select the control path.
    """
    instruction = re.split(r"(?:文件|文本)?内容(?:如下|为|是)?(?:[（(][^）)]*[）)])?[：:]", text, maxsplit=1)[0].strip()
    if re.match(r"^(?:(?:请|你|能不能|能|可以|可否|帮我|一下|只)\s*)*(?:解释|说明|介绍|讲解|如何|怎么|怎样)", instruction):
        return False
    if re.match(r"^[‘’\"“`「]", instruction) or re.search(r"(?:不要|不必|无需|不用|别)(?:实际)?(?:创建|新建|生成|写入|写文件|保存)", instruction):
        return False
    write = re.search(r"(?:创建|新建|生成|写入|写到|写成|保存|存到|写一).*(?:文件|[A-Za-z]:[\\/]|\.[A-Za-z0-9]+)|(?:文件|文本).*(?:写入|写到|写成|保存|存到)", instruction, re.S)
    read = re.search(r"(?:读回|读取|再读|读出|打开.*(?:正文|内容))", instruction, re.S)
    return bool(write and read)


def same_path(left, right):
    return isinstance(left, str) and isinstance(right, str) and bool(left.strip()) and bool(right.strip()) and os.path.normcase(os.path.abspath(left)) == os.path.normcase(os.path.abspath(right))


def literal_content(text):
    marker = re.search(r"(?:文件|文本)?内容如下(?:[（(][^）)]*[）)])?[：:](?:\r?\n)?", text)
    return text[marker.end():] if marker else None


def edited_file_request(previous, text):
    """Path-only edits keep the body; an explicit new body replaces it."""
    if literal_content(text) is not None:
        return text
    # A request to generate a new version no longer provides an exact body.
    # Editing a target or explicitly preserving text cannot erase its contract.
    rewrite = re.search(r"改写|重写|重新生成|改成新版|换成新版", text)
    keep = re.search(r"路径|文件名|(?:正文|内容)(?:保持)?不变", text)
    return text if rewrite and not keep else previous


def literal_content_error(text, name, arguments):
    """Check a supplied literal body; never fill in the model's arguments.

    Only the explicit trailing '内容如下：' form owns this byte contract.
    A formatting newline after its delimiter is not part of the body.
    """
    if name != "write_file":
        return ""
    body = literal_content(text)
    if body is not None and arguments.get("content") != body:
        actual = arguments.get("content", "")
        mismatch = next((i for i, (left, right) in enumerate(zip(body, actual)) if left != right), min(len(body), len(actual)))
        return ("write_file.content 与用户在内容如下之后给出的字面正文不一致；"
                f"首个差异在第{mismatch + 1}个字符，原文此处为{body[mismatch:mismatch + 24]!r}，"
                f"提案此处为{actual[mismatch:mismatch + 24]!r}。"
                "原文行首也属于正文，不是行号提示；逐字保留，不增删或改写")
    return ""


def writes_for(task, session_id, actions):
    return [a for a in actions if a["session_id"] == session_id and a["task_id"] == task["id"] and a["tool"] == "write_file"]


def read_for(action, task, session_id):
    """Require contiguous post-write pages of the same bytes, task and path."""
    receipt = action.get("receipt") or {}
    chunks, refs, size, position = [], [], None, 0
    for record in task.get("tool_results", []):
        result = record["result"]
        content = result.get("content")
        if (record["tool"] == "read_file" and record.get("session_id") == session_id
                and record.get("task_id") == task["id"]
                and action["action_id"] in record.get("after_actions", [])
                and same_path(record["arguments"].get("path"), action["arguments"].get("path"))
                and same_path(result.get("path"), action["arguments"].get("path"))
                and result.get("ok") is True and isinstance(content, str)):
            offset = result.get("offset")
            if offset == 0:
                chunks, refs, size, position = [], [], result.get("size"), 0
            if offset != position or result.get("size") != size:
                continue
            chunks.append(content)
            refs.append(record["result_ref"])
            position += len(content.encode("utf-8"))
            if result.get("truncated") is False and result.get("next_offset") is None and position == size:
                full = "".join(chunks)
                if hashlib.sha256(full.encode("utf-8")).hexdigest() == receipt.get("sha256"):
                    return {"result": {"content": full}, "result_ref": ", ".join(refs)}
            elif result.get("next_offset") != position:
                chunks, refs, size, position = [], [], None, 0
    return None


def completion_error(task, session_id, actions, mode, *, require_proposal=False):
    writes = writes_for(task, session_id, actions)
    if not writes or (require_proposal and not any(a["action_id"] in task.get("delivery_actions", []) for a in writes)):
        if mode == "clarify":
            return ""
        return "原文件任务尚缺真实 write_file 提案；chat 自报不是任务完成证据"
    for action in writes:
        if action["status"] == "succeeded" and not read_for(action, task, session_id):
            return "写入已经成功，禁止重写；原文件任务尚缺同一路径的完整 read_file 结果，请继续实际读取"
    return ""


def render_file_delivery(task, session_id, actions, fallback, *, require_proposal=False):
    writes = writes_for(task, session_id, actions)
    if require_proposal and not any(a["action_id"] in task.get("delivery_actions", []) for a in writes):
        return fallback
    if not writes:
        return fallback
    active = [a for a in writes if a["status"] != "cancelled"]
    complete = bool(active) and all(a["status"] == "succeeded" and read_for(a, task, session_id) for a in active)
    if complete:
        lines = ["文件任务已完成：确认后写入成功，并已实际调用 read_file 读回核对。"]
        for action in active:
            record = read_for(action, task, session_id)
            lines.extend([f"文件：{action['arguments']['path']}（读取记录 {record['result_ref']}）", "完整内容：", record["result"]["content"]])
        return "\n".join(lines)
    return fallback + "\n文件任务尚未完成：写入及随后独立读取、完整交付尚未全部核验。"
