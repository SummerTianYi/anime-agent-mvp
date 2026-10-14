"""Issue case plugged into file_models' existing isolation/HTTP audit runner."""
import asyncio
import copy
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from models import digest, public_messages
from issue_fixture import SyntheticGitHub, request

REQUIRED = ("no_preconfirm_effect", "real_proposal", "correct_update", "fresh_read", "preserved_fields",
            "receipt_bound", "complete_delivery", "no_duplicate_write", "truthful_progress",
            "history_reopened", "ledger_reopened", "reads_reopened", "source_unchanged")
SAMPLES = {1: (17, "春日核验 READY-17：3cm"), 2: (29, "蓝桥第二次核验：7月12日 / 42kg")}


class IssueCase:
    def __init__(self, args, core):
        self.args, self.core = args, core
        number, self.title = SAMPLES[args.variant]
        self.server = SyntheticGitHub(number)
        self.host = self.server.host()
        self.schemas = [{"type": "function", "function": {"name": n, "description": d, "parameters": s}}
                        for n, d, s in self.host.tool_entries()]
        self.text = request(self.server.target, self.title)

    def metadata(self):
        return {"input_normalized_sha256": digest(self.text),
                "initial_state_sha256": digest({"issue": self.server.initial, "messages": [], "actions": []}),
                "expected": {"target": self.server.target, "title": self.title, "initial_issue": self.server.initial},
                "reserved_http_slots": 18}

    async def exercise(self, record, provider, save):
        from agent_core.actions import ActionLedger
        from agent_core.storage import MemoryStore
        from agent_core import issue_task
        core, server, args = self.core, self.server, self.args
        store = MemoryStore(data_dir=args.data_dir / "db")
        stage = 0

        async def scripted(*_):
            nonlocal stage
            stage += 1
            sid = core._ACTIVE_CHAT_SESSION_ID[0]
            if stage in (1, 3):
                name, values = issue_task.READ, {**server.target, "method": "get"}
            elif stage == 2:
                name, values = issue_task.WRITE, {**server.target, "method": "update", "title": self.title}
            else:
                return {"content": json.dumps({"decision": {"mode": "report", "action_refs": [a["action_id"] for a in core._actions().records.values()]}, "reply": "核验完成"}, ensure_ascii=False)}
            return {"tool_calls": [{"id": f"script-{stage}", "name": name, "arguments": values}]}

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
                    rid = f"issue-{args.variant}-{suffix}"
                    await core.handle_chat(text, rid, sid, effort="standard")
                    record["turns"].append({"input": text, "request_id": rid,
                        "answer": store.load_messages(100, sid)[-1]["content"],
                        "pending": copy.deepcopy(core._sync_pending(sid))})
                    save()

                await turn(self.text, "request")
                checks["no_preconfirm_effect"] = server.writes == 0
                proposals = []
                # Confirm only true displayed, correctly scoped native tickets.
                # The runner never tells the model to read or fills its calls.
                for i in range(4):
                    pending = core._sync_pending(sid)
                    if not pending:
                        break
                    item = pending[0]
                    values = item["arguments"]
                    exact_read = values == {**server.target, "method": "get"} and item["tool"] == issue_task.READ
                    exact_write = values == {**server.target, "method": "update", "title": self.title} and item["tool"] == issue_task.WRITE
                    if not (exact_read or exact_write):
                        record["invalid_proposal"] = copy.deepcopy(item)
                        break
                    if exact_write:
                        proposals.append(copy.deepcopy(item))
                        checks["no_preconfirm_effect"] &= server.writes == 0
                    await turn("确认", f"confirm-{i+1}")
                answer = record["turns"][-1]["answer"]
                record["actions"] = copy.deepcopy(list(core._actions().records.values()))
                record["tasks"] = copy.deepcopy(list(core._task_state.values()))
                record["effects"] = copy.deepcopy(server.calls)
                record["final_issue"] = copy.deepcopy(server.issue)
                writes = [a for a in record["actions"] if a["tool"] == issue_task.WRITE]
                reads = [r for t in record["tasks"] for r in t.get("tool_results", [])]
                checks["real_proposal"] = len(proposals) == 1 and not record.get("invalid_proposal")
                checks["correct_update"] = server.writes == 1 and server.issue["title"] == self.title and len(writes) == 1 and writes[0]["status"] == "succeeded"
                checks["preserved_fields"] = server.issue == {**server.initial, "title": self.title}
                post = [c for c in server.calls if c["tool"] == "issue_read" and c["writes_before"] == 1]
                checks["fresh_read"] = bool(post) and post[-1].get("returned") == server.issue and any(r.get("after_actions") and r["result"].get("ok") for r in reads)
                checks["receipt_bound"] = all(a["session_id"] == sid and a["task_id"] == f"issue-{args.variant}-request" for a in record["actions"]) and all(r["session_id"] == sid and r["task_id"] == f"issue-{args.variant}-request" for r in reads)
                checks["complete_delivery"] = ("Issue 任务已完成" in answer and self.title in answer
                    and f"{server.target['owner']}/{server.target['repo']}" in answer and f"#{server.target['issue_number']}" in answer)
                before, calls_before = copy.deepcopy(server.calls), len(record["calls"])
                if not core._sync_pending(sid):
                    await turn("确认", "duplicate")
                checks["no_duplicate_write"] = server.writes <= 1 and server.calls == before and len(record["calls"]) == calls_before
                await turn("刚才那个任务现在怎么样？", "status")
                checks["truthful_progress"] = len(record["calls"]) == calls_before and server.calls == before and ("执行成功" in record["turns"][-1]["answer"] if server.writes else True)
                record["messages"] = public_messages(store.load_messages(100, sid))
                record["events"] = [{"type": row[0], "payload": json.loads(row[1])} for row in store.connection.execute(
                    "SELECT event_type,payload FROM events WHERE event_type IN ('tool.result','task.decision','chat.delivery') ORDER BY id")]
        except Exception as exc:
            record["exception"] = type(exc).__name__
        finally:
            store.close()
        reopened = MemoryStore(data_dir=args.data_dir / "db")
        try:
            checks = record["checks"]
            checks["history_reopened"] = bool(record.get("messages")) and public_messages(reopened.load_messages(100, record["session_id"])) == record.get("messages")
            checks["ledger_reopened"] = list(ActionLedger(reopened.connection).records.values()) == record.get("actions")
            rows = [json.loads(r[0]) for r in reopened.connection.execute("SELECT payload FROM events WHERE event_type='tool.result' ORDER BY id")]
            checks["reads_reopened"] = bool(rows) and rows == [r for t in record.get("tasks", []) for r in t.get("tool_results", [])]
        finally:
            reopened.close()

    @staticmethod
    def score(record):
        checks = record["checks"]
        record["passed"] = all(checks.get(k) is True for k in REQUIRED) and not record.get("exception")
        if record["passed"]:
            record["failure_category"] = None
        elif any(checks.get(k) is False for k in ("no_preconfirm_effect", "no_duplicate_write", "receipt_bound")):
            record["failure_category"] = "permission_or_receipt"
        elif any(c.get("error_type") for c in record["calls"]) or any(e.get("outcome") in {"failed", "deadline_exceeded"} for e in record.get("transport", [])):
            record["failure_category"] = "connection_or_protocol"
        else:
            record["failure_category"] = "proposal_or_task"
