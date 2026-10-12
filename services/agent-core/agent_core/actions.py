"""Codex V1: durable, parameter-bound ask actions. No permission is granted here.

The Core still evaluates its permission engine before proposal AND execution.
Executing is persisted before I/O: after a crash it becomes UNKNOWN, never retried.
"""
from __future__ import annotations
import copy
import hashlib
import json
import os
import re
import time
import uuid


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def args_hash(tool, arguments):
    normalized = copy.deepcopy(arguments)
    if tool == "write_file":
        normalized["mode"] = str(normalized.get("mode") or "overwrite").strip().lower()
        if isinstance(normalized.get("path"), str):
            normalized["path"] = os.path.normcase(os.path.abspath(normalized["path"]))
    return hashlib.sha256(canonical([tool, normalized]).encode()).hexdigest()


def decision(text):
    # Quoted/code literals and an explicitly delimited write/mail payload are
    # task data, not permission instructions. This classifier never grants
    # authorization from a substring; ambiguous prose still requires a ticket.
    control = re.sub(
        r'\x60{3}[\s\S]*?\x60{3}|\x60[^\x60]*\x60|"(?:\\.|[^"\\])*"|“[^”]*”|‘[^’]*’|「[^」]*」'
        r'|(?<![A-Za-z0-9])\x27(?:\\.|[^\x27\\])*\x27(?![A-Za-z0-9])', " ", text)
    payload = re.search(r"(写成|写入|保存为|改成|改为|(?:内容|正文)(?:如下|为)?)\s*[:：]", control)
    # A topic such as "关于邮件内容：" is not evidence of a data payload.
    if payload and (payload.group(1) in {"写成","写入","保存为","改成","改为"}
                    or re.search(r"发送|发(?:一封)?邮件|写|保存|记录|草拟|新建|追加", control[:payload.start()])):
        control = control[:payload.end()-1]
    normalized = re.sub(r"[\s。！!，,；;]", "", control).lower()
    if (re.search(r"不同意|不确认|不要|(?<!分)别(?:执行|写|发)|先不|拒绝|取消|算了|放弃|不执行|不发送|不允许", normalized)
            or re.search(r"\b(?:no|cancel|stop)\b|\b(?:don't|don’t|do\s+not)\s+(?:send|write|execute|run)\b", control.lower())):
        return "edit" if re.search(r"改成|改为|改发|换成|重新|改一下", normalized) else "decline"
    if re.search(r"改成|改为|改发|换成|改一下", normalized):
        return "edit"
    affirmative = re.sub(r"[\s。！!，,；;]", "", text).lower()
    if re.fullmatch(r"(?:确认|同意|可以|执行吧|好的|去吧|ok|yes|确认执行|同意执行)", affirmative):
        return "approve"
    return "other"


class ActionLedger:
    def __init__(self, connection):
        self.db = connection
        self.db.execute("CREATE TABLE IF NOT EXISTS harness_actions (id TEXT PRIMARY KEY, session_id INTEGER, payload TEXT NOT NULL)")
        self.records = {}
        for row in self.db.execute("SELECT payload FROM harness_actions"):
            item = json.loads(row[0])
            self.records[item["action_id"]] = item
            if item["status"] == "executing":
                item["status"] = "unknown"
                item["receipt"] = {"ok": False, "outcome": "unknown", "error": "上次执行中断；结果未知，禁止自动重试"}
                self.save(item)
        self.db.commit()

    def save(self, item):
        self.db.execute("INSERT OR REPLACE INTO harness_actions VALUES (?,?,?)",
                        (item["action_id"], item["session_id"], canonical(item)))
        self.db.commit()

    def pending(self, session):
        items = []
        for item in self.records.values():
            if item["session_id"] == session and item["status"] == "awaiting_confirmation":
                if time.time() > item["expires"]:
                    item["status"] = "expired"
                    self.save(item)
                else:
                    items.append(item)
        return items

    def task_items(self, session, task):
        return [r for r in self.records.values() if r["session_id"] == session and r["task_id"] == task]

    def propose(self, session, task, request_id, tool, arguments):
        fingerprint = args_hash(tool, arguments)
        # UNKNOWN is session-wide across task changes: a casual rephrase cannot resend.
        for item in self.records.values():
            if item["session_id"] == session and item["args_hash"] == fingerprint:
                if item["status"] in {"unknown", "executing"} or item["task_id"] == task:
                    return item
        revision = 1 + max((r["revision"] for r in self.task_items(session, task) if r["tool"] == tool), default=0)
        item = dict(action_id=uuid.uuid4().hex, task_id=task, session_id=session, revision=revision,
                    tool=tool, arguments=copy.deepcopy(arguments), args_hash=fingerprint,
                    request_id=request_id, expires=time.time()+600, status="awaiting_confirmation", receipt=None)
        self.records[item["action_id"]] = item
        self.save(item)
        return item

    def ticket(self, item):
        return {k: item[k] for k in ("action_id", "revision", "args_hash")}

    def cancel(self, session):
        cancelled = []
        for item in self.pending(session):
            item["status"] = "cancelled"
            self.save(item)
            cancelled.append(item)
        return cancelled

    async def execute(self, session, ticket, request_id, permitted, executor):
        item = self.records.get(str(ticket.get("action_id", "")))
        if (not item or item["session_id"] != session or self.ticket(item) != ticket
                or item["status"] != "awaiting_confirmation" or time.time() > item["expires"]
                or args_hash(item["tool"], item["arguments"]) != item["args_hash"]):
            return {"ok":False,"outcome":"rejected","error":"确认已失效或参数版本不一致；未执行"}
        if not permitted(item["tool"], item["arguments"]):
            item["status"] = "failed"
            item["receipt"] = {"ok":False,"outcome":"denied","error":"当前权限不再允许此动作"}
            self.save(item)
            return self.result(item)
        item.update(status="executing", confirmation_request_id=request_id, execution_id=uuid.uuid4().hex)
        self.save(item)
        try:
            receipt = await executor(item["tool"], copy.deepcopy(item["arguments"]))
            item["status"] = "unknown" if receipt.get("outcome") == "unknown" else "succeeded" if receipt.get("ok") is True else "failed"
            item["receipt"] = copy.deepcopy(receipt)
        except BaseException as exc:
            # An exception after dispatch does not prove the mutation did not happen.
            item["status"] = "unknown"
            item["receipt"] = {"ok":False,"outcome":"unknown","error":f"执行结果未知（{type(exc).__name__}）；禁止自动重试"}
            self.save(item)
            if not isinstance(exc, Exception):
                raise
        self.save(item)
        return self.result(item)

    def result(self, item):
        result = copy.deepcopy(item["receipt"] or {"ok":False})
        # Keep the original MCP envelope durably in receipt; the model consumes
        # its normalized output, not duplicate text/blob copies from the wire.
        result.pop("raw_result", None)
        result.update(action_id=item["action_id"], revision=item["revision"], args_hash=item["args_hash"],
                      outcome=item["status"], execution_id=item.get("execution_id"),
                      confirmation_request_id=item.get("confirmation_request_id"))
        if item["status"] == "awaiting_confirmation":
            result.update(needs_confirmation=True, confirmation=self.ticket(item),
                          error="操作尚未执行。等待用户确认当前动作；不要重复调用或声称完成。")
        elif item["status"] in {"cancelled","expired"}:
            result.update(ok=False, error="旧动作已取消或过期；不能复用旧授权")
        return result

    def context(self, session, task):
        return [{"tool":a["tool"], "arguments":a["arguments"], "receipt":self.result(a)}
                for a in self.task_items(session, task)]
