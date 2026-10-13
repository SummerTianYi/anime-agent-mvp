"""Independent Harness V1 safety regressions; no real provider, filesystem DB or MCP.

Run from services/agent-core with: python -B -m unittest discover -s tests
-p test_harness_v1_review.py -v

Direct execution prints REVIEW_METRICS with the number of assertions actually
executed. HARNESS_REVIEW_CORE_ROOT may select a git-exported agent-core directory
for a before/after run of this exact test file. Tests import a private package
alias so they cannot reuse or mutate another suite's agent_core.main globals.
"""
from __future__ import annotations

import asyncio
import copy
import hashlib
import importlib
import json
import os
from pathlib import Path
import socket
import sqlite3
import sys
from contextlib import ExitStack
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch
import uuid


ASSERTION_COUNTS: dict[str, int] = {}
_ISOLATION = None
_GUARD_INSTALLED = False
CORE_ROOT = Path(os.environ.get("HARNESS_REVIEW_CORE_ROOT") or Path(__file__).resolve().parents[1])
FALSE_SUCCESS = "审查夹具：全部操作已经成功完成"
SEND_ARGS = {"to": "audit@example.invalid", "subject": "fixture", "body": "fixture"}


def _audit_guard(event, args):
    """Deny external effects even if a fixture accidentally misses a mock."""
    state = _ISOLATION
    if state is None:
        return
    forbidden = False
    if event == "open":
        path, mode, flags = args
        if isinstance(path, (str, bytes)):
            name = os.fsdecode(path).replace(chr(92), "/").rsplit("/", 1)[-1].lower()
            forbidden = name == ".env" or name.startswith(".env.")
        forbidden = forbidden or bool(
            flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)
        )
    elif event == "sqlite3.connect":
        forbidden = str(args[0]) != ":memory:"
    elif event == "socket.connect":
        # Windows asyncio builds its internal wakeup socketpair over loopback.
        # Only that exact stdlib implementation may connect; no service is used.
        forbidden = sys._getframe(1).f_code is not getattr(socket.socketpair, "__code__", None)
    elif event in {
        "subprocess.Popen", "os.system", "os.mkdir", "os.remove", "os.rename",
        "os.rmdir", "os.truncate", "os.link", "os.symlink",
    }:
        forbidden = True
    if forbidden:
        state.append(event)
        raise RuntimeError("independent-review isolation blocked: " + event)


def _memory_init(self, data_dir=None):
    self.path = Path(":memory:")
    self.connection = sqlite3.connect(":memory:", check_same_thread=False)
    self.connection.row_factory = sqlite3.Row
    self._migrate()


def _reply(text=FALSE_SUCCESS):
    return json.dumps({"reply": text, "emotion": "neutral", "gesture": "none"}, ensure_ascii=False)


def _call(name, arguments, call_id="fixture-call"):
    return {"id": call_id, "name": name, "arguments": copy.deepcopy(arguments)}


class IndependentReviewTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        global _ISOLATION, _GUARD_INSTALLED
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.blocked_io = []
        previous_isolation = _ISOLATION
        _ISOLATION = self.blocked_io
        self.stack.callback(self._restore_isolation, previous_isolation)
        if not _GUARD_INSTALLED:
            sys.addaudithook(_audit_guard)
            _GUARD_INSTALLED = True
        ASSERTION_COUNTS[self._testMethodName] = 0
        self.stack.enter_context(patch.object(sys, "dont_write_bytecode", True))
        self.root = Path.cwd() / "__review_virtual_allowed__"
        self.stack.enter_context(patch.dict(os.environ, {
            "LLM_PROVIDER": "mock",
            "ANIME_AGENT_TTS": "0",
            "ANIME_AGENT_WAKE_WORD": "0",
            "ANIME_AGENT_MCP_SERVERS": "",
            "ANIME_AGENT_VOICE_INPUT_MODE": "manual",
            "ANIME_AGENT_ALLOWED_COMMANDS": "",
            "ANIME_AGENT_WRITE_ROOTS": str(self.root),
            "ANIME_AGENT_TOOLS_ROOTS": str(self.root),
        }))
        self.stack.enter_context(patch("dotenv.load_dotenv", return_value=False))

        alias = "_independent_review_core_" + uuid.uuid4().hex
        package = ModuleType(alias)
        package.__path__ = [str(CORE_ROOT / "agent_core")]
        package.__package__ = alias
        sys.modules[alias] = package
        self.stack.callback(self._unload, alias)
        storage = importlib.import_module(alias + ".storage")
        with patch.object(storage.MemoryStore, "__init__", _memory_init):
            self.core = importlib.import_module(alias + ".main")
        self.stack.callback(self.core.memory.close)
        self.McpServer = importlib.import_module(alias + ".mcp_host").McpServer
        self.core.hub = SimpleNamespace(send_roles=AsyncMock(), role_count=lambda *_: 0)
        self.core.broadcast_state = AsyncMock()
        self.core.broadcast_behavior = AsyncMock()
        self.core._spawn = lambda coro: coro.close()
        self.core.tools_schema = [{
            "type": "function",
            "function": {"name": "get_time", "parameters": {"type": "object", "properties": {}}},
        }]
        # Core now requires proposals to name advertised tools. Preserve these
        # synthetic permission/unknown/budget probes by registering their tools.
        self.core.tools_schema.extend([
            {"type": "function", "function": {"name": name, "parameters": {"type": "object"}}}
            for name in ("write_file", "mcp__fixture__send_email")
        ])
        self.core.provider = SimpleNamespace(
            complete_with_tools=AsyncMock(return_value={"content": _reply()}),
            complete=AsyncMock(return_value=_reply()),
        )
        self.sid = self.core.memory.create_session()["id"]
        self.core._ACTIVE_CHAT_SESSION_ID[0] = self.sid
        self.book = self.core._actions()
        self.core._task_state[self.sid] = {
            "id": "review-task", "intent": "办理合成夹具任务", "blocked": False,
        }
        self.effects = []

        async def executor(name, arguments):
            self.effects.append((name, copy.deepcopy(arguments)))
            return {"ok": True, "output": "fixture accepted"}

        self.real_executor = self.core._execute_authorized_tool
        self.core._execute_authorized_tool = executor

    @staticmethod
    def _restore_isolation(previous):
        global _ISOLATION
        _ISOLATION = previous

    @staticmethod
    def _unload(alias):
        for name in list(sys.modules):
            if name == alias or name.startswith(alias + "."):
                del sys.modules[name]

    def expect(self, condition, message):
        """Count each explicit behavioral/isolation assertion, including failures."""
        ASSERTION_COUNTS[self._testMethodName] += 1
        self.assertTrue(condition, message)

    def tearDown(self):
        self.expect(not self.blocked_io, "fixture attempted forbidden IO: " + repr(self.blocked_io))

    def latest_reply(self):
        return self.core.memory.load_messages(100, self.sid)[-1]["content"]

    async def propose(self, arguments=None):
        return await self.core.run_tool(
            "mcp__fixture__send_email", copy.deepcopy(SEND_ARGS if arguments is None else arguments)
        )

    async def chat(self, text, request_id, **kwargs):
        await asyncio.wait_for(self.core.handle_chat(text, request_id, self.sid, **kwargs), timeout=10)

    async def _duplicate_approval(self, explicit_second_ticket):
        first = await self.propose(SEND_ARGS | {"to": "first@example.invalid"})
        second = await self.propose(SEND_ARGS | {"to": "second@example.invalid"})
        self.core.hub.send_roles.reset_mock()
        dispatched = asyncio.Event()
        release_receipt = asyncio.Event()

        async def executor(name, arguments):
            self.effects.append((name, copy.deepcopy(arguments)))
            if len(self.effects) == 1:
                dispatched.set()
                await release_receipt.wait()
            return {"ok": True, "output": "fixture accepted"}

        self.core._execute_authorized_tool = executor
        first_chat = asyncio.create_task(self.chat("确认", "first-approval", confirmation=first["confirmation"]))
        duplicate = None
        try:
            await asyncio.wait_for(dispatched.wait(), timeout=3)
            pending_events = [
                call.args[1] for call in self.core.hub.send_roles.call_args_list
                if call.args[1].get("type") == "permission.pending"
            ]
            self.expect(not pending_events, "the next action was already displayed; race fixture is invalid")
            kwargs = {"confirmation": first["confirmation"]} if explicit_second_ticket else {}
            duplicate = asyncio.create_task(self.chat("确认", "duplicate-approval", **kwargs))
            for _ in range(4):
                await asyncio.sleep(0)
        finally:
            release_receipt.set()
            await asyncio.gather(first_chat, *([duplicate] if duplicate is not None else []))
        self.expect(
            [args["to"] for _, args in self.effects] == ["first@example.invalid"],
            "duplicate confirmation dispatched a different recipient",
        )
        self.expect(
            self.book.records[second["action_id"]]["status"] == "awaiting_confirmation",
            "the independent second action must remain pending",
        )
        return second

    async def test_p1_unbound_duplicate_cannot_authorize_next_parameters(self):
        await self._duplicate_approval(explicit_second_ticket=False)

    async def test_control_explicit_ticket_double_click_then_fresh_ticket(self):
        second = await self._duplicate_approval(explicit_second_ticket=True)
        await self.chat("确认", "fresh-second-approval", confirmation=second["confirmation"])
        self.expect(
            [args["to"] for _, args in self.effects] == ["first@example.invalid", "second@example.invalid"],
            "a fresh explicit ticket must still execute the intended next action exactly once",
        )

    async def test_p1_cancel_received_before_dispatch_revokes_queued_approval(self):
        await self._cancel_queued_approval("取消")

    # Follow-up independent review found these classifier counterexamples;
    # parent executes their integration consequences in this isolated fixture.
    async def test_cancel_contractions_revokes_queued_approval(self):
        await self._cancel_queued_approval("Don't send it. Please cancel. That's final.")

    async def test_cancel_after_topic_label_revokes_queued_approval(self):
        await self._cancel_queued_approval("关于邮件内容：不要发送，取消这项操作。")

    async def test_cancel_spaced_negation_revokes_queued_approval(self):
        await self._cancel_queued_approval("不 确认")

    async def _cancel_queued_approval(self, text):
        proposal = await self.propose()
        await self.core.chat_lock.acquire()
        approval = asyncio.create_task(self.chat("确认", "queued-approval", confirmation=proposal["confirmation"]))
        cancel = None
        try:
            await asyncio.sleep(0)
            cancel = asyncio.create_task(self.chat(text, "queued-cancel"))
            # chat() uses wait_for, so allow both wrapped handlers to reach the lock.
            for _ in range(4):
                await asyncio.sleep(0)
            self.expect(not self.effects, "fixture dispatched before receiving cancellation")
        finally:
            self.core.chat_lock.release()
            await asyncio.gather(approval, *([cancel] if cancel is not None else []))
        self.expect(not self.effects, "an approval queued before cancellation still dispatched afterward")
        self.expect(
            self.book.records[proposal["action_id"]]["status"] == "cancelled",
            "cancelled pending action did not retain a cancelled receipt",
        )

    def memory_mcp(self, replies):
        server = self.McpServer("fixture", [])
        server.started = True
        self.wire = []
        server.process = SimpleNamespace(
            stdin=SimpleNamespace(write=self.wire.append, drain=AsyncMock()),
            stdout=SimpleNamespace(readline=AsyncMock(
                side_effect=[json.dumps(item).encode() + b"\n" for item in replies] + [b""]
            )),
        )
        self.core.mcp_host.servers["fixture"] = server
        self.core._execute_authorized_tool = self.real_executor
        return server

    async def test_p1_mcp_same_id_reverse_request_is_not_a_success_receipt(self):
        self.memory_mcp([
            {"jsonrpc": "2.0", "id": 1, "method": "ping"},
            {"jsonrpc": "2.0", "id": 1, "result": {
                "isError": True, "content": [{"type": "text", "text": "FIXTURE_REJECTED"}],
            }},
        ])
        proposal = await self.propose()
        await self.chat("确认", "confirm-mcp", confirmation=proposal["confirmation"])
        item = self.book.records[proposal["action_id"]]
        self.expect(item["status"] in {"failed", "unknown"}, "reverse request became a succeeded ledger entry")
        self.expect(item["receipt"].get("ok") is not True, "missing tool reply became ok=true")
        self.expect("连接器已接受发送" not in self.latest_reply(), "failed tool advertised accepted delivery")
        self.expect(FALSE_SUCCESS not in self.latest_reply(), "model success replaced an adverse MCP receipt")

    async def test_p1_mcp_missing_result_cannot_be_accepted_as_success(self):
        self.memory_mcp([{"jsonrpc": "2.0", "id": 1}])
        proposal = await self.propose()
        await self.chat("确认", "malformed-mcp", confirmation=proposal["confirmation"])
        item = self.book.records[proposal["action_id"]]
        self.expect(item["status"] in {"failed", "unknown"}, "malformed envelope became succeeded")
        self.expect("连接器已接受发送" not in self.latest_reply(), "malformed envelope produced a delivery claim")

    async def test_control_valid_mcp_success_receipt_is_preserved(self):
        self.memory_mcp([{"jsonrpc": "2.0", "id": 1, "result": {
            "content": [{"type": "text", "text": "FIXTURE_ACCEPTED"}],
        }}])
        proposal = await self.propose()
        await self.chat("确认", "valid-mcp", confirmation=proposal["confirmation"])
        item = self.book.records[proposal["action_id"]]
        self.expect(item["status"] == "succeeded", "valid MCP result must remain a successful receipt")
        self.expect(item["receipt"].get("ok") is True, "valid MCP ok flag was lost")
        self.expect("FIXTURE_ACCEPTED" in self.latest_reply(), "connector evidence was lost in final delivery")

    async def test_p1_reused_unknown_receipt_blocks_resend_and_false_success(self):
        item = self.book.propose(self.sid, "old-task", "origin", "mcp__fixture__send_email", SEND_ARGS)

        async def lost_ack(*_):
            raise TimeoutError("fixture lost acknowledgement")

        await self.book.execute(self.sid, self.book.ticket(item), "old-approval", lambda *_: True, lost_ack)
        self.expect(item["status"] == "unknown", "fixture failed to create a genuine unknown execution")
        self.core.provider.complete_with_tools.side_effect = [
            {"tool_calls": [_call("mcp__fixture__send_email", SEND_ARGS)]},
            {"content": _reply()},
        ]
        await self.chat("继续刚才的发送任务", "resume-unknown")
        self.expect(not self.effects, "unknown action was dispatched again")
        self.expect(item["status"] == "unknown", "unknown status was overwritten during reuse")
        self.expect(FALSE_SUCCESS not in self.latest_reply(), "model fabricated success after unknown reuse")
        self.expect("未知" in self.latest_reply(), "final reply omitted the authoritative unknown outcome")

    async def test_p1_permission_denial_without_action_receipt_cannot_claim_success(self):
        outside = str(self.root.parent / "__review_virtual_forbidden__" / "fixture.txt")
        self.core.provider.complete_with_tools.side_effect = [
            {"tool_calls": [_call("write_file", {"path": outside, "content": "fixture"})]},
            {"content": _reply()},
        ]
        await self.chat("写入合成测试文件", "denied-write")
        self.expect(not self.effects, "permission-denied write reached the executor")
        self.expect(FALSE_SUCCESS not in self.latest_reply(), "empty ledger allowed a false completion claim")
        self.expect(
            any(word in self.latest_reply() for word in ("拒绝", "未执行", "失败", "不允许", "权限")),
            "final delivery did not expose the denied operation",
        )

    async def test_p1_post_tools_model_failure_still_charges_shared_budget(self):
        rounds = 0

        async def batch(*_):
            nonlocal rounds
            rounds += 1
            return {"tool_calls": [
                _call("mcp__fixture__send_email", SEND_ARGS | {"subject": f"batch-{rounds}-{i}"}, str(i))
                for i in range(6)
            ]}

        self.core.provider.complete_with_tools.side_effect = batch
        self.core.provider.complete.side_effect = self.core.ProviderError("fixture failure after tools")
        await self.chat("发送一批合成夹具", "budget-origin", effort="chill")
        original_task = self.core._task_state[self.sid]["id"]
        for index in range(3):
            pending = self.book.pending(self.sid)
            self.expect(bool(pending), "initial six proposals unexpectedly disappeared")
            await self.chat(
                "确认", f"budget-confirm-{index}", effort="chill",
                confirmation=self.book.ticket(pending[0]),
            )
        task = self.core._task_state[self.sid]
        self.expect(task["id"] == original_task, "confirmations silently created a fresh task")
        self.expect(len(self.book.records) <= 6, "post-tools failures replenished the six-call proposal budget")
        self.expect(rounds <= 3, "post-tools failures exceeded the three-round budget")
        self.expect(task["calls_used"] >= 6, "already issued tool calls were not charged after model failure")
        self.expect(task["rounds_used"] >= 1, "already issued model/tool rounds were not charged")

    async def test_p1_no_pending_continue_does_not_refill_call_budget_or_effort(self):
        self.core.provider.complete_with_tools.return_value = {
            "tool_calls": [_call("get_time", {}, str(i)) for i in range(6)],
        }
        self.core.provider.complete.return_value = _reply("预算已用完")
        await self.chat("执行同一项多步查询", "calls-origin", effort="chill")
        original_task = self.core._task_state[self.sid]["id"]
        self.expect(len(self.effects) == 6, "fixture did not consume the six-call budget")
        self.expect(not self.book.pending(self.sid), "fixture unexpectedly has pending ask actions")
        plain_calls = self.core.provider.complete.await_count
        await self.chat("继续", "calls-continuation", effort="deep")
        self.expect(len(self.effects) == 6, "no-pending continuation refilled exhausted calls")
        self.expect(self.core._task_state[self.sid]["id"] == original_task, "continuation lost task identity")
        self.expect(self.core._task_state[self.sid]["budget"]["max_calls"] == 6, "effort dial refilled old task")
        self.expect(self.core.provider.complete.await_count == plain_calls, "exhausted call budget leaked a plain completion")

    async def test_p1_no_pending_continue_does_not_refill_round_budget(self):
        self.core.provider.complete_with_tools.return_value = {"tool_calls": [_call("get_time", {})]}
        self.core.provider.complete.return_value = _reply("轮次已用完")
        await self.chat("逐步执行同一项查询", "rounds-origin", effort="chill")
        self.expect(len(self.effects) == 3, "fixture did not consume three tool rounds")
        self.expect(self.core.provider.complete_with_tools.await_count == 3, "fixture model round count differs")
        plain_calls = self.core.provider.complete.await_count
        await self.chat("继续", "rounds-continuation", effort="chill")
        self.expect(len(self.effects) == 3, "continuation refilled exhausted tool rounds")
        self.expect(self.core.provider.complete_with_tools.await_count == 3, "continuation requested an extra tool round")
        self.expect(self.core.provider.complete.await_count == plain_calls, "exhausted round budget leaked a plain completion")


def run_review_suite():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(IndependentReviewTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    metrics = {
        "tests_run": result.testsRun,
        "assertions_executed": sum(ASSERTION_COUNTS.values()),
        "assertions_by_test": dict(sorted(ASSERTION_COUNTS.items())),
        "failed_tests": [test._testMethodName for test, _ in result.failures],
        "error_tests": [test._testMethodName for test, _ in result.errors],
        "skipped_tests": [test._testMethodName for test, _ in result.skipped],
        "passed": result.wasSuccessful(),
        "source_sha256": {
            name: hashlib.sha256((CORE_ROOT / "agent_core" / name).read_bytes()).hexdigest()
            for name in ("main.py", "actions.py", "agent_loop.py", "mcp_host.py")
        },
        "test_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    print("REVIEW_METRICS=" + json.dumps(metrics, ensure_ascii=False, sort_keys=True))
    return result.wasSuccessful()


if __name__ == "__main__":
    sys.exit(0 if run_review_suite() else 1)
