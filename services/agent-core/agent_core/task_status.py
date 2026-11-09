"""Narrow, read-only questions about existing ledger tasks; no model intent API."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import PureWindowsPath
import re

from .actions import decision as confirmation_decision
from .action_delivery import describe


@dataclass(frozen=True)
class StatusQuestion:
    subject: str


def _target_names(item):
    names = [str(item["task_id"]), str(item["action_id"])]
    for key in ("path", "to", "title"):
        value = item["arguments"].get(key)
        if isinstance(value, str):
            names.append(value)
            if key == "path":
                names.append(PureWindowsPath(value).name)
    return {name.casefold() for name in names}


def status_question(text: str, records=(), session_id=None) -> StatusQuestion | None:
    # Recognize complete progress questions, never filter generated sentences.
    # Commands mixed into a question deliberately remain in the existing
    # confirmation/edit flow. Quoted examples and conversational subjects do not
    # match these task references.
    # Keep spaces inside literal targets (e.g. "review draft.txt").
    value = text.strip().rstrip("？?。！!").strip()
    value = re.sub(r"^(?:请|麻烦你?|帮我)?(?:查看|查询|查一下|看一下|看看|告诉我|说一下)?\s*", "", value)
    if value in {"还有哪些没完成", "还有哪些未完成", "哪些还在待确认", "哪些还没执行"}:
        return StatusQuestion(subject="")
    outcome = (r"(?:完成|成功|失败|取消|结束|搞定|解决|"
               r"(?:执行|处理|写入|保存)(?:完成|成功|完毕|完|好)?|(?:写|做|办|弄)(?:完|好|妥))")
    match = re.fullmatch(
        r"(?P<subject>.*?)\s*(?:现在|目前|如今)?\s*(?:都)?(?:"
        r"(?:进度|进展|状态|执行结果)(?:是(?:什么|怎样)|如何|怎么样|怎样|呢|如何了|怎么样了)?|"
        r"(?:是什么状态|是什么进度|什么情况)|"
        r"(?:怎么样|怎样|到哪一步|处理到哪一步|执行到哪一步|做得怎么样|进行得怎么样)(?:了)?|"
        r"(?:有结果|办好|做好|弄好)(?:了)?(?:吗|没|没有)|"
        rf"(?:已经|还没|还没有|尚未)?(?:被)?{outcome}(?:了)?(?:吗|了吗|没|没有)|"
        rf"(?:是否|有没有|是不是)(?:已经)?(?:被)?{outcome}(?:了)?|"
        r"(?:还|是否)(?:需要|要|在等|待)(?:我)?确认(?:吗)?|"
        r"是成功还是失败|还在吗)", value)
    if not match:
        return None
    subject = match["subject"].rstrip("，, ").removesuffix("的").strip()
    generic = re.fullmatch(
        r"(?:你)?(?:(?:刚才|刚刚|之前|先前|上次|当前)(?:的)?)?"
        r"(?:(?:这|那)(?:个|些|件|项)|所有|全部|各项)?(?:的)?"
        r"(?:任务|待办|操作|事情|事|文件|文件写入|邮件|Issue|issue)", subject)
    relational = re.fullmatch(r"(?:刚才|之前|上次)(?:让你|请你|交给你)(?:做|办|处理|写)?的(?:事|任务|文件)", subject)
    if generic or relational or subject in {"上个任务", "各项待办"}:
        return StatusQuestion(subject="")
    # Explicit identifiers and file targets may be resolved ONLY in this
    # session. Unknown references get a host clarification, not another task.
    # A task-prefixed COMMAND is not an identifier. In particular, never
    # swallow "任务先取消，再告诉我状态" before the existing revocation gate.
    if len(subject) > 1 and (subject[0], subject[-1]) in {('"', '"'), ('“', '”'), ('`', '`')}:
        subject = subject[1:-1]
    identifier = re.fullmatch(r"(?:任务|动作|会话|另一会话|其他会话)[:：]?\s*[A-Za-z0-9_.:-]+", subject)
    file_target = re.fullmatch(r"(?:[A-Za-z]:[\\/])?[^，,；;：“”\"<>]+\.[A-Za-z0-9]{1,10}", subject)
    if file_target and confirmation_decision(subject) in {"decline", "edit"}:
        # Existing literal filenames may contain control words. Otherwise a
        # command ending in a filename must retain its existing revocation
        # semantics, including before the turn lock / queued dispatch.
        if not any(item["session_id"] == session_id and subject.casefold() in _target_names(item) for item in records):
            return None
    if identifier or file_target:
        return StatusQuestion(subject=(subject.removeprefix("任务").removeprefix("动作").strip("：: ") if identifier and not file_target else subject))
    return None


def render_task_status(question: StatusQuestion, records, session_id):
    items = [item for item in records if item["session_id"] == session_id]
    if question.subject:
        targets = {question.subject.casefold(), re.sub(r"^(?:刚才|之前|当前|那个|这个)(?:的)?", "", question.subject).casefold()}
        selected_tasks = set()
        for item in items:
            if targets & _target_names(item):
                selected_tasks.add(item["task_id"])
        items = [item for item in items if item["task_id"] in selected_tasks]
    if not items:
        return "当前会话中没有找到对应的已登记操作。请指明任务或文件；本次没有确认、执行或重试操作。", []
    labels = {"awaiting_confirmation": "待确认，尚未执行", "executing": "执行中，尚无最终结果",
              "succeeded": "执行成功", "failed": "执行失败", "cancelled": "已取消，未执行",
              "unknown": "结果未知，未自动重试", "expired": "授权已过期，未执行"}
    groups = {}
    for item in items:
        groups.setdefault(item["task_id"], []).append(item)
    lines = []
    for index, actions in enumerate(groups.values(),1):
        counts = Counter(labels.get(a["status"], "状态待核验") for a in actions)
        if len(groups)>1 or len(actions)>1:
            lines.append(f"第{index}组：" + "，".join(f"{label} {count}项" for label, count in counts.items()))
        for item in actions:
            args = item["arguments"]
            label = labels.get(item["status"], "状态待核验")
            if item["status"] == "succeeded" and item["tool"].endswith("send_email"):
                label = "邮件服务已接受发送"
            lines.append(describe(item["tool"],args) + "：" + label)
    return "\n".join(lines), items
