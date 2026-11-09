"""Independent response-boundary counterexamples through real adapters/chat.

The shared fixture audits against disk writes, production databases, network,
and subprocesses. All provider transport returns synthetic bytes or HTTP errors.
"""
from __future__ import annotations

import copy
import ast
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import unittest
import urllib.error

import test_harness_v1_review as fixture
from test_provider_response_boundary import call, encode, response


def chat_text(text: str = "正常对照：一起聊音乐。") -> str:
    return json.dumps({"decision": {"mode": "chat"}, "reply": text}, ensure_ascii=False)


class ProviderResponseReviewTests(fixture.IndependentReviewTests):
    def provider(self, dialect: str, replies: list) -> object:
        cls = self.core.OpenAICompatibleProvider if dialect == "openai" else self.core.AnthropicCompatibleProvider
        provider = cls(name="review-" + dialect, base_url="https://example.invalid/v1",
                       model="synthetic-review", api_key="synthetic-review-key", timeout_seconds=3)
        self.wire_requests = []
        queue = list(replies)

        def wire(request):
            self.wire_requests.append(json.loads(request.data))
            if not queue:
                raise AssertionError("unexpected provider retry/fallback")
            item = queue.pop(0)
            if isinstance(item, Exception):
                raise item
            return item

        provider._request = wire
        return provider

    def errors(self) -> list[str]:
        return [item.args[1].get("message", "") for item in self.core.hub.send_roles.call_args_list
                if item.args[1].get("type") == "core.error"]

    async def bad_chat(self, dialect: str, raw: bytes, label: str) -> None:
        self.core.provider = self.provider(dialect, [raw])
        before = copy.deepcopy(self.book.records)
        effects = copy.deepcopy(self.effects)
        await self.chat("请调用已注册工具处理合成审查任务", label)
        self.assertEqual(self.book.records, before)
        self.assertEqual(self.effects, effects)
        self.assertEqual(len(self.wire_requests), 1)
        self.assertIn("模型答复未能完成", self.latest_reply())
        self.assertTrue(self.errors())
        self.assertNotIn("Traceback", " ".join(self.errors()))
        self.assertNotIn("DO_NOT_LEAK", " ".join(self.errors()))

    async def test_http_protocol_error_must_not_fall_back_to_plain_success(self) -> None:
        for dialect in ("openai", "anthropic"):
            for status in (400, 404, 422):
                with self.subTest(dialect=dialect, status=status):
                    error = urllib.error.HTTPError("https://example.invalid", status, "synthetic", {},
                                                   io.BytesIO(b'{"error":'))
                    self.core.provider = self.provider(dialect, [error, response(dialect, chat_text("伪正常补答"))])
                    await self.chat("请调用已注册工具处理合成审查任务", f"http-{dialect}-{status}")
                    print("PROVIDER_REVIEW_HTTP " + json.dumps({"dialect": dialect, "status": status,
                        "requests": len(self.wire_requests), "reply": self.latest_reply(),
                        "actions": len(self.book.records), "effects": len(self.effects)}, ensure_ascii=False))
                    self.assertEqual(len(self.wire_requests), 1, "protocol error became unsupported-tools fallback")
                    self.assertIn("模型答复未能完成", self.latest_reply())
                    self.assertEqual(self.effects, [])
                    self.assertEqual(self.book.records, {})

    async def test_http_error_body_does_not_reach_core_error_ui(self) -> None:
        for dialect in ("openai", "anthropic"):
            for message in ("Traceback DO_NOT_LEAK", {"Traceback": "DO_NOT_LEAK"}):
                with self.subTest(dialect=dialect, message=message):
                    self.core.hub.send_roles.reset_mock()
                    # 403 isolates HTTP-body parsing from the pre-existing
                    # transport retry of temporary 5xx responses.
                    error = urllib.error.HTTPError("https://example.invalid", 403, "synthetic", {},
                                                   io.BytesIO(encode({"error": {"message": message}})))
                    self.core.provider = self.provider(dialect, [error])
                    await self.chat("请调用已注册工具处理合成审查任务", f"unsafe-http-{dialect}-{type(message).__name__}")
                    self.assertEqual(len(self.wire_requests), 1)
                    self.assertTrue(self.errors())
                    self.assertNotIn("Traceback", " ".join(self.errors()))
                    self.assertNotIn("DO_NOT_LEAK", " ".join(self.errors()))
                    self.assertEqual(self.book.records, {})
                    self.assertEqual(self.effects, [])

    async def test_well_formed_http_argument_error_does_not_mean_tools_unsupported(self) -> None:
        raw = encode({"error": {"type": "invalid_request_error",
                               "message": "tool input is malformed JSON"}})
        for dialect in ("openai", "anthropic"):
            with self.subTest(dialect=dialect):
                error = urllib.error.HTTPError("https://example.invalid", 400, "synthetic", {}, io.BytesIO(raw))
                self.core.provider = self.provider(dialect, [error, response(dialect, chat_text("伪正常补答"))])
                await self.chat("请调用已注册工具处理合成审查任务", "argument-http-" + dialect)
                self.assertEqual(len(self.wire_requests), 1)
                self.assertIn("模型答复未能完成", self.latest_reply())
                self.assertEqual(self.book.records, {})
                self.assertEqual(self.effects, [])

    async def test_explicit_tools_unsupported_keeps_plain_chat_compatibility(self) -> None:
        for dialect in ("openai", "anthropic"):
            for message in ("no tools", "This model does not support function calling.",
                            "Unsupported parameter: 'tools'"):
                with self.subTest(dialect=dialect, message=message):
                    error = urllib.error.HTTPError("https://example.invalid", 400, "synthetic", {},
                        io.BytesIO(encode({"error": {"message": message}})))
                    self.core.provider = self.provider(dialect, [error, response(dialect, chat_text())])
                    await self.chat("请调用时间工具", "supported-fallback-" + dialect)
                    self.assertEqual(len(self.wire_requests), 2)
                    self.assertIn("没有取得可核验的操作回执", self.latest_reply())
                    # The compatible plain response is still obtained on the second wire
                    # request. It cannot serve as a receipt for an explicit external task.
                    self.assertNotIn("tools", self.wire_requests[-1])
                    self.assertEqual(self.book.records, {})
                    self.assertEqual(self.effects, [])

    async def test_anthropic_nonassistant_or_nonmessage_envelope_cannot_propose(self) -> None:
        for field, value in (("role", "user"), ("role", {}), ("type", "error"), ("type", [])):
            with self.subTest(field=field, value=value):
                raw = json.loads(response("anthropic", calls=[call(fixture.SEND_ARGS, "mcp__fixture__send_email")]))
                raw[field] = value
                await self.bad_chat("anthropic", encode(raw), "wrong-envelope-" + field)

    async def test_anthropic_explicit_message_envelope_keeps_text_and_tools(self) -> None:
        raw = json.loads(response("anthropic", chat_text()))
        raw.update(type="message", role="assistant")
        self.core.provider = self.provider("anthropic", [encode(raw)])
        await self.chat("天依，来聊音乐", "explicit-message")
        self.assertEqual(self.latest_reply(), "正常对照：一起聊音乐。")
        self.assertEqual(self.effects, [])
        raw = json.loads(response("anthropic", calls=[call({})]))
        raw.update(type="message", role="assistant")
        self.core.provider = self.provider("anthropic", [encode(raw), b"{}"])
        await self.chat("请调用合成时间工具", "explicit-tool-message")
        self.assertEqual(self.effects, [("get_time", {})])
        self.assertEqual(len(self.wire_requests), 2)

    async def test_actual_observer_keeps_surrogate_bytes_for_provider_error(self) -> None:
        """Reuse the existing exact-class extraction, then real adapter/chat."""
        root = Path(__file__).resolve().parents[3]
        folder = root / "docs/assessments/root-cause-repair/a4-pilot/repro"

        def load(name, path):
            spec = importlib.util.spec_from_file_location(name, path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module

        review = load("provider_observer_review", folder / "file_runner_review.py")
        projection = load("provider_observer_projection", folder / "models.py")
        tree = ast.parse((folder / "file_models.py").read_text(encoding="utf-8"))
        raw = b'{"choices":[{"message":{"content":"\\ud800"}}]}'
        adapter = self.core.OpenAICompatibleProvider

        class Parent(adapter):
            def __init__(self):
                super().__init__(name="review-observer", base_url="https://example.invalid", model="synthetic",
                                 api_key="synthetic-key", timeout_seconds=3)

            def _request(self, request):
                return raw

        ledger, record, saves = {"cap": 48, "attempts": []}, {"calls": []}, []

        def save():
            # Real runner save uses this JSON/UTF-8 boundary; no disk is needed.
            saves.append(json.dumps(record, ensure_ascii=False).encode("utf-8"))

        observed = review.make_observer(tree, projection, Parent, ledger, record, save)
        observed._request.__func__.__globals__["hashlib"] = hashlib
        self.core.provider = observed
        await self.chat("天依，来聊音乐", "observer-surrogate")
        self.assertIn("模型答复未能完成", self.latest_reply())
        self.assertEqual(len(record["calls"]), 1)
        self.assertEqual(len(ledger["attempts"]), 1)
        self.assertEqual(record["calls"][0]["response_parse_error"], "UnicodeEncodeError")
        self.assertEqual(record["calls"][0]["response_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertNotIn("response", record["calls"][0])
        self.assertEqual(self.effects, [])
        self.assertGreaterEqual(len(saves), 2)

    async def test_unpaired_surrogates_and_nonfinite_exponents_are_controlled(self) -> None:
        for dialect in ("openai", "anthropic"):
            for arguments in ('{"nested":{"amount":1e999}}', '{"nested":["\\ud800"]}'):
                with self.subTest(dialect=dialect, arguments=arguments):
                    await self.bad_chat(dialect, response(dialect, calls=[call(arguments)]), "nested-" + dialect)

    async def test_overdeep_wire_json_is_controlled_before_any_action(self) -> None:
        raw = b'{"nested":' + b"[" * 1500 + b"0" + b"]" * 1500 + b"}"
        for dialect in ("openai", "anthropic"):
            with self.subTest(dialect=dialect):
                await self.bad_chat(dialect, raw, "deep-" + dialect)

    async def test_nested_duplicate_arguments_cannot_choose_a_target(self) -> None:
        for dialect in ("openai", "anthropic"):
            with self.subTest(dialect=dialect):
                await self.bad_chat(dialect, response(dialect, calls=[call(
                    '{"recipient":{"to":"first@example.invalid","to":"second@example.invalid"}}',
                    "mcp__fixture__send_email")]), "duplicate-target-" + dialect)

    async def test_mixed_batch_both_orders_has_no_ticket_or_effect(self) -> None:
        valid = call(fixture.SEND_ARGS, "mcp__fixture__send_email", "valid")
        invalid = call('{"target":', "get_time", "invalid")
        for dialect in ("openai", "anthropic"):
            for calls in ([valid, invalid], [invalid, valid]):
                with self.subTest(dialect=dialect, first=calls[0]["id"]):
                    await self.bad_chat(dialect, response(dialect, calls=calls), "ordered-" + dialect)

    async def test_valid_call_with_invalid_text_block_is_atomic(self) -> None:
        for dialect in ("openai", "anthropic"):
            with self.subTest(dialect=dialect):
                raw = json.loads(response(dialect, calls=[call(fixture.SEND_ARGS, "mcp__fixture__send_email")]))
                if dialect == "openai":
                    raw["choices"][0]["message"]["content"] = [{"type": "text", "text": False}]
                else:
                    raw["content"].append({"type": "text", "text": False})
                await self.bad_chat(dialect, encode(raw), "bad-block-" + dialect)

    async def test_error_envelope_cannot_hide_a_valid_call(self) -> None:
        for dialect in ("openai", "anthropic"):
            with self.subTest(dialect=dialect):
                raw = json.loads(response(dialect, calls=[call(fixture.SEND_ARGS, "mcp__fixture__send_email")]))
                raw["error"] = {"message": "DO_NOT_LEAK"}
                await self.bad_chat(dialect, encode(raw), "error-envelope-" + dialect)

    async def test_wrong_call_type_or_missing_name_cannot_be_guessed(self) -> None:
        for dialect in ("openai", "anthropic"):
            for damage in ("name", "type"):
                with self.subTest(dialect=dialect, damage=damage):
                    raw = json.loads(response(dialect, calls=[call(fixture.SEND_ARGS, "mcp__fixture__send_email")]))
                    item = raw["choices"][0]["message"]["tool_calls"][0] if dialect == "openai" else raw["content"][0]
                    if damage == "name":
                        (item["function"] if dialect == "openai" else item).pop("name")
                    else:
                        item["type"] = "custom"
                    await self.bad_chat(dialect, encode(raw), f"missing-{dialect}-{damage}")

    async def test_schema_invalid_call_beyond_execution_budget_blocks_front(self) -> None:
        for dialect in ("openai", "anthropic"):
            with self.subTest(dialect=dialect):
                calls = [call({}, "get_time", f"read-{n}") for n in range(25)]
                calls[0] = call(fixture.SEND_ARGS, "mcp__fixture__send_email", "front-write")
                calls.append(call({}, "unregistered_tool", "tail"))
                # Schema-invalid arguments retain the existing bounded model
                # correction turn. It is distinct from a wire protocol error.
                self.core.provider = self.provider(dialect, [response(dialect, calls=calls),
                                                            response(dialect, chat_text("参数不合法，未执行。"))])
                await self.chat("请调用已注册工具处理合成审查任务", "long-batch-" + dialect)
                self.assertEqual(self.book.records, {})
                self.assertEqual(self.effects, [])
                self.assertEqual(len(self.wire_requests), 2)

    async def test_empty_content_zero_argument_tool_executes_once(self) -> None:
        for dialect in ("openai", "anthropic"):
            with self.subTest(dialect=dialect):
                self.effects.clear()
                self.core.provider = self.provider(dialect, [response(dialect, calls=[call({})]), b'{"broken":'])
                await self.chat("请调用合成时间工具", "zero-args-" + dialect)
                self.assertEqual(self.effects, [("get_time", {})])
                self.assertEqual(len(self.wire_requests), 2)
                self.assertIn("fixture accepted", self.latest_reply())
                self.assertNotIn("尚未执行", self.latest_reply())

    async def test_text_blocks_survive_actual_handle_chat(self) -> None:
        text = chat_text()
        for dialect in ("openai", "anthropic"):
            with self.subTest(dialect=dialect):
                parts = [{"type": "text", "text": text[:12]}, {"type": "text", "text": text[12:]}]
                raw = response(dialect, parts) if dialect == "openai" else encode({"content": parts})
                self.core.provider = self.provider(dialect, [raw])
                await self.chat("你好，天依", "text-blocks-" + dialect)
                self.assertEqual(self.latest_reply(), "正常对照：一起聊音乐。")
                self.assertEqual(len(self.wire_requests), 1)
                self.assertEqual(self.effects, [])

    async def test_failed_operation_retains_failed_receipt_after_bad_supplement(self) -> None:
        for dialect in ("openai", "anthropic"):
            with self.subTest(dialect=dialect):
                self.effects.clear()
                self.core.provider = self.provider(dialect, [response(dialect, calls=[
                    call(fixture.SEND_ARGS, "mcp__fixture__send_email")]), b"\xff"])
                await self.chat("请调用合成发送服务", "failed-propose-" + dialect)
                pending = self.book.pending(self.sid)
                self.assertEqual(len(pending), 1)

                async def failure(name, arguments):
                    self.effects.append((name, copy.deepcopy(arguments)))
                    return {"ok": False, "error": "合成服务明确拒绝"}

                self.core._execute_authorized_tool = failure
                await self.chat("确认", "failed-confirm-" + dialect, confirmation=self.book.ticket(pending[0]))
                self.assertEqual(pending[0]["status"], "failed")
                self.assertEqual(len(self.effects), 1)
                self.assertEqual(len(self.wire_requests), 2)
                self.assertIn("失败", self.latest_reply())
                self.assertNotIn("已接受发送", self.latest_reply())

    async def test_mixed_supplement_preserves_success_and_unknown_without_extra_operation(self) -> None:
        for dialect in ("openai", "anthropic"):
            for unknown in (False, True):
                with self.subTest(dialect=dialect, unknown=unknown):
                    self.effects.clear()
                    proposal = call(fixture.SEND_ARGS | {"subject": f"review-{dialect}-{unknown}"},
                                    "mcp__fixture__send_email")
                    invalid_supplement = response(dialect, calls=[call({}, id="valid-read"),
                                                                 call("[null]", id="broken-tail")])
                    self.core.provider = self.provider(dialect, [response(dialect, calls=[proposal]), invalid_supplement])
                    await self.chat("请调用合成发送服务", f"mixed-propose-{dialect}-{unknown}")
                    pending = self.book.pending(self.sid)
                    self.assertEqual(len(pending), 1)

                    async def operation(name, arguments):
                        self.effects.append((name, copy.deepcopy(arguments)))
                        if unknown:
                            raise TimeoutError("synthetic missing operation receipt")
                        return {"ok": True, "output": "fixture accepted"}

                    self.core._execute_authorized_tool = operation
                    await self.chat("确认", f"mixed-confirm-{dialect}-{unknown}", confirmation=self.book.ticket(pending[0]))
                    self.assertEqual(len(self.effects), 1)
                    self.assertEqual(len(self.wire_requests), 2)
                    self.assertEqual(pending[0]["status"], "unknown" if unknown else "succeeded")
                    self.assertIn("结果未知" if unknown else "邮件服务已接受发送", self.latest_reply())
                    self.assertNotIn("尚未执行", self.latest_reply())
                    self.assertEqual(self.book.pending(self.sid), [])


def load_tests(loader, tests, pattern):
    return unittest.TestSuite(ProviderResponseReviewTests(name) for name in ProviderResponseReviewTests.__dict__
                              if name.startswith("test_"))
