"""Email scenario for the existing isolated, counted Provider runner."""
import asyncio
import copy
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from models import digest, public_messages
from email_fixture import SEND, SyntheticGmail, request

REQUIRED = ("no_preconfirm_effect", "real_proposal", "accepted_once", "exact_parameters",
            "receipt_bound", "complete_delivery", "no_duplicate_send", "truthful_progress",
            "history_reopened", "ledger_reopened", "mailbox_reopened", "source_unchanged")
SAMPLES = {1: ("qingzhu@example.invalid", "青竹合成回执 175", "第一行：Error 是正常正文\n第二行：蓝桥 42kg"),
           2: ("lanqiao.29@example.invalid", "蓝桥第二次核验：7月12日", "请保留原句：取消订单是测试文字\n完整末行 READY 902，长度3cm")}


class EmailCase:
    def __init__(self, args, core):
        self.args, self.core = args, core
        to, subject, body = SAMPLES[args.variant]
        self.expected = dict(to=[to], subject=subject, body=body)
        self.server = SyntheticGmail(args.data_dir / "synthetic-mailbox.json")
        self.host = self.server.host()
        self.schemas = [{"type": "function", "function": {"name": n, "description": d, "parameters": s}}
                        for n, d, s in self.host.tool_entries()]
        self.text = request(to, subject, body)

    def exact(self, values):
        return (set(values) <= {"to", "subject", "body", "mimeType"}
                and values.get("mimeType", "text/plain") == "text/plain"
                and all(values.get(k) == v for k, v in self.expected.items()))

    def metadata(self):
        return {"input_normalized_sha256": digest(self.text),
                "initial_state_sha256": digest({"mailbox": [], "messages": [], "actions": []}),
                "expected": self.expected, "reserved_http_slots": 18}

    async def exercise(self, record, provider, save):
        from agent_core.actions import ActionLedger, args_hash
        from agent_core.storage import MemoryStore
        core, server, args = self.core, self.server, self.args
        store = MemoryStore(data_dir=args.data_dir / "db")

        async def scripted(*_):
            actions = list(core._actions().records.values())
            if not actions:
                return {"tool_calls": [{"id": "controlled-send", "name": SEND, "arguments": self.expected}]}
            return {"content": json.dumps({"decision": {"mode": "report", "action_refs": [a["action_id"] for a in actions]}, "reply": "发送请求已受理"}, ensure_ascii=False)}

        try:
            with patch.multiple(core, memory=store, provider=provider or SimpleNamespace(complete_with_tools=scripted),
                    tools_schema=[], tool_registry={}, mcp_host=self.host,
                    hub=SimpleNamespace(send_roles=AsyncMock(), role_count=lambda *_: 0),
                    broadcast_state=AsyncMock(), broadcast_behavior=AsyncMock(), _spawn=lambda c: c.close(),
                    _action_ledger=None, _task_state={}, _result_pages={}, _pending_writes={},
                    _shown_confirmations={}, chat_lock=asyncio.Lock()):
                sid = store.create_session()["id"]
                record["session_id"] = sid
                checks = record["checks"]

                async def turn(text, suffix):
                    rid = f"email-{args.variant}-{suffix}"
                    await core.handle_chat(text, rid, sid, effort="standard")
                    record["turns"].append({"input": text, "request_id": rid,
                        "answer": store.load_messages(100, sid)[-1]["content"],
                        "pending": copy.deepcopy(core._sync_pending(sid))})
                    save()

                await turn(self.text, "request")
                checks["no_preconfirm_effect"] = not server.calls and not server.mailbox
                pending = core._sync_pending(sid)
                checks["real_proposal"] = len(pending) == 1 and pending[0]["tool"] == SEND and self.exact(pending[0]["arguments"])
                if checks["real_proposal"] and checks["no_preconfirm_effect"]:
                    await turn("确认", "confirm")
                record["actions"] = copy.deepcopy(list(core._actions().records.values()))
                record["tasks"] = copy.deepcopy(list(core._task_state.values()))
                record["effects"] = copy.deepcopy(server.calls)
                record["mailbox"] = copy.deepcopy(server.mailbox)
                actions = record["actions"]
                checks["accepted_once"] = len(server.calls) == len(server.mailbox) == len(actions) == 1 and actions[0]["status"] == "succeeded"
                checks["exact_parameters"] = len(server.mailbox) == 1 and self.exact(server.mailbox[0]["arguments"]) and server.mailbox[0]["recipients"] == self.expected["to"]
                # Independent service-side receipt comparison, not the product verifier.
                checks["receipt_bound"] = bool(checks["accepted_once"] and actions[0]["session_id"] == sid
                    and actions[0]["task_id"] == f"email-{args.variant}-request"
                    and actions[0]["args_hash"] == args_hash(SEND, server.mailbox[0]["arguments"])
                    and actions[0]["receipt"].get("ok") is True
                    and actions[0]["receipt"].get("raw_result") == {"content": [{"type": "text", "text": "Email sent successfully with ID: " + server.mailbox[0]["id"]}]})
                answer = record["turns"][-1]["answer"]
                checks["complete_delivery"] = bool(checks["receipt_bound"] and all(s in answer for s in (
                    "发送请求已受理", self.expected["to"][0], self.expected["subject"], self.expected["body"], server.mailbox[0]["id"]))
                    and "已送达" not in answer and "已经收到" not in answer and "已被阅读" not in answer)
                before, calls_before = copy.deepcopy(server.calls), len(record["calls"])
                if not core._sync_pending(sid):
                    await turn("确认", "duplicate")
                checks["no_duplicate_send"] = len(server.calls) <= 1 and server.calls == before and len(record["calls"]) == calls_before
                await turn("刚才那个任务现在怎么样？", "status")
                checks["truthful_progress"] = server.calls == before and len(record["calls"]) == calls_before and ("连接器已接受发送" in record["turns"][-1]["answer"] if server.mailbox else True)
                record["messages"] = public_messages(store.load_messages(100, sid))
                record["events"] = [{"type": row[0], "payload": json.loads(row[1])} for row in store.connection.execute(
                    "SELECT event_type,payload FROM events WHERE event_type IN ('task.decision','chat.delivery') ORDER BY id")]
        except Exception as exc:
            record["exception"] = type(exc).__name__
        finally:
            store.close()
        reopened = MemoryStore(data_dir=args.data_dir / "db")
        try:
            checks = record["checks"]
            checks["history_reopened"] = bool(record.get("messages")) and public_messages(reopened.load_messages(100, record["session_id"])) == record.get("messages")
            checks["ledger_reopened"] = list(ActionLedger(reopened.connection).records.values()) == record.get("actions")
            checks["mailbox_reopened"] = server.mailbox_path.exists() and json.loads(server.mailbox_path.read_text(encoding="utf-8")) == record.get("mailbox")
        finally:
            reopened.close()

    @staticmethod
    def score(record):
        checks = record["checks"]
        record["passed"] = all(checks.get(k) is True for k in REQUIRED) and not record.get("exception")
        if record["passed"]:
            record["failure_category"] = None
        elif any(checks.get(k) is False for k in ("no_preconfirm_effect", "no_duplicate_send")):
            record["failure_category"] = "permission_or_receipt"
        elif any(c.get("error_type") for c in record["calls"]) or any(e.get("outcome") in {"failed", "deadline_exceeded"} for e in record.get("transport", [])):
            record["failure_category"] = "connection_or_protocol"
        elif checks.get("accepted_once") and not checks.get("receipt_bound"):
            record["failure_category"] = "permission_or_receipt"
        else:
            record["failure_category"] = "proposal_or_task"
