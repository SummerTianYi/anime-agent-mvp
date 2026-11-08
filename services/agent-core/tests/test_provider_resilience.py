"""Codex: isolated transport fault regressions; no real credentials or services."""
from __future__ import annotations

import io
import asyncio
import http.client
import http.server
import json
import socket
import ssl
import threading
import time
import unittest
import urllib.error
from unittest.mock import Mock, patch

from agent_core.main import OpenAICompatibleProvider, ProviderError
from agent_core.provider_http import REQUEST_ID, category, retry_delay, route_for
from agent_core.agent_loop import run_agent_loop


def reply(text="recovered"):
    return json.dumps({"choices": [{"message": {"content": text}}]}).encode()


def provider(**kwargs):
    return OpenAICompatibleProvider(
        name="deepseek", base_url="https://chatapi.weixin.qq.com/openai/v1",
        model="test-model", api_key="synthetic-secret", timeout_seconds=2, **kwargs,
    )


class ProviderResilienceTests(unittest.IsolatedAsyncioTestCase):
    async def test_reset_recovers_without_restarting_chat(self):
        p = provider()
        p._request = Mock(side_effect=[ConnectionResetError(10054, "reset"), reply()])
        self.assertEqual(await p.complete([{"role": "user", "content": "test"}]), "recovered")
        self.assertEqual(p._request.call_count, 2)

    async def test_temporary_gateway_error_recovers(self):
        p = provider()
        error = urllib.error.HTTPError(p.completion_url, 503, "busy", {}, io.BytesIO(b"{}"))
        p._request = Mock(side_effect=[error, reply()])
        self.assertEqual(await p.complete_with_tools([], []),
                         {"content": "recovered", "tool_calls": [], "raw": {"content": "recovered"}})

    async def test_current_domestic_endpoint_does_not_depend_on_system_proxy(self):
        p = provider()
        with patch("urllib.request.build_opener") as build:
            response = build.return_value.open.return_value.__enter__.return_value
            response.read1.side_effect = [reply(), b""]
            response.length = 0
            import urllib.request
            p._request(urllib.request.Request(p.completion_url))
        self.assertEqual(len(build.call_args.args), 1)
        self.assertEqual(build.call_args.args[0].proxies, {})

    async def test_three_attempt_limit_and_same_instance_recovers_later(self):
        events = []
        p = provider(on_transport_event=events.append)
        p._request = Mock(side_effect=[ConnectionResetError()] * 3 + [reply("next turn")])
        with self.assertRaises(ProviderError):
            await p.complete([])
        self.assertEqual(p._request.call_count, 3)
        self.assertEqual(await p.complete([]), "next turn")
        self.assertEqual([e["outcome"] for e in events], ["retry", "retry", "failed", "ok"])

    async def test_permanent_http_errors_do_not_retry(self):
        for code in (400, 401, 403, 404, 407, 422, 429):
            with self.subTest(code=code):
                p = provider()
                p._request = Mock(side_effect=urllib.error.HTTPError(p.completion_url, code, "secret", {}, io.BytesIO(b"secret")))
                with self.assertRaises(ProviderError) as raised:
                    await p.complete([])
                self.assertNotIn("secret", str(raised.exception))
                self.assertEqual(p._request.call_count, 1)

    async def test_certificate_failure_never_disables_validation_or_retries(self):
        p = provider()
        p._request = Mock(side_effect=urllib.error.URLError(ssl.SSLCertVerificationError(1, "untrusted")))
        with self.assertRaisesRegex(ProviderError, "证书校验失败"):
            await p.complete([])
        self.assertEqual(p._request.call_count, 1)

    async def test_dns_failure_recovers(self):
        p = provider()
        p._request = Mock(side_effect=[urllib.error.URLError(socket.gaierror(-3, "temporary")), reply()])
        self.assertEqual(await p.complete([]), "recovered")

    async def test_incomplete_response_recovers(self):
        p = provider()
        p._request = Mock(side_effect=[http.client.IncompleteRead(b"half", 5), reply()])
        self.assertEqual(await p.complete([]), "recovered")

    async def test_short_retry_after_is_honored(self):
        p = provider()
        p._request = Mock(side_effect=[urllib.error.HTTPError(p.completion_url, 429, "slow", {"Retry-After": "0.05"}, io.BytesIO(b"{}")), reply()])
        waiting, release = asyncio.Event(), asyncio.Event()

        async def hold_backoff(seconds):
            waiting.set()
            await release.wait()

        with patch("agent_core.provider_http.asyncio.sleep", side_effect=hold_backoff) as sleep:
            request = asyncio.create_task(p.complete([]))
            try:
                await asyncio.wait_for(waiting.wait(), 2)
                sleep.assert_awaited_once_with(.05)
                self.assertEqual(p._request.call_count, 1)
                self.assertFalse(request.done())
            finally:
                release.set()
                result = await asyncio.wait_for(request, 2)
        self.assertEqual(result, "recovered")
        self.assertEqual(p._request.call_count, 2)

    async def test_long_retry_after_never_overruns_budget(self):
        p = provider()
        p._request = Mock(side_effect=urllib.error.HTTPError(p.completion_url, 503, "slow", {"Retry-After": "120"}, io.BytesIO(b"{}")))
        started = time.monotonic()
        with self.assertRaises(ProviderError):
            await p.complete([])
        self.assertLess(time.monotonic() - started, 1)
        self.assertEqual(p._request.call_count, 1)

    async def test_deadline_covers_slow_worker_and_late_result_is_discarded(self):
        events = []
        p = provider(on_transport_event=events.append)
        p.timeout_seconds = .05
        def slow(_):
            time.sleep(.2)
            return reply("late")
        p._request = Mock(side_effect=slow)
        started = time.monotonic()
        with self.assertRaisesRegex(ProviderError, "超时"):
            await p.complete([])
        self.assertLess(time.monotonic() - started, .18)
        await asyncio.sleep(.23)
        self.assertEqual(p._request.call_count, 1)
        self.assertEqual([e["outcome"] for e in events], ["deadline_exceeded"])
        p._request = Mock(return_value=reply())
        self.assertEqual(await p.complete([]), "recovered")

    async def test_cancel_during_backoff_stops_retry(self):
        retried = asyncio.Event()
        p = provider(on_transport_event=lambda e: retried.set() if e["outcome"] == "retry" else None)
        p._request = Mock(side_effect=[ConnectionResetError(), reply("must not run")])
        task = asyncio.create_task(p.complete([]))
        await asyncio.wait_for(retried.wait(), 1)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        await asyncio.sleep(.4)
        self.assertEqual(p._request.call_count, 1)

    async def test_cancel_slow_model_never_executes_returned_tool(self):
        p = provider()
        entered = threading.Event()
        release = threading.Event()
        def slow(_):
            entered.set()
            release.wait(1)
            return tool_reply()
        p._request = Mock(side_effect=slow)
        calls = []
        async def execute(name, args):
            calls.append(name)
            return {"ok": True}
        task = asyncio.create_task(run_agent_loop(p, [], [{}], execute))
        await asyncio.to_thread(entered.wait, 1)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        release.set()
        await asyncio.sleep(.08)
        self.assertEqual(calls, [])

    async def test_post_tool_network_retry_does_not_execute_tool_twice(self):
        p = provider()
        p._request = Mock(side_effect=[tool_reply(), ConnectionResetError(), reply("done")])
        calls = []
        async def execute(name, args):
            calls.append(name)
            return {"ok": True, "result": "one side effect"}
        result = await run_agent_loop(p, [], [{}], execute)
        self.assertEqual(result.text, "done")
        self.assertEqual(calls, ["test_write"])
        bodies = [c.args[0].data for c in p._request.call_args_list]
        self.assertEqual(bodies[1], bodies[2])
        self.assertEqual(json.loads(bodies[2])["messages"][-1]["role"], "tool")

    async def test_diagnostics_are_correlated_and_do_not_log_secrets(self):
        events = []
        p = provider(on_transport_event=events.append)
        p._request = Mock(side_effect=[ConnectionResetError(10054, "synthetic-secret PRIVATE-TEXT"), reply()])
        token = REQUEST_ID.set("test-request-42")
        try:
            await p.complete([{"role": "user", "content": "PRIVATE-TEXT"}])
        finally:
            REQUEST_ID.reset(token)
        dump = json.dumps(events)
        self.assertNotIn("synthetic-secret", dump)
        self.assertNotIn("PRIVATE-TEXT", dump)
        self.assertEqual(events[0]["category"], "connection_reset")
        self.assertEqual(events[0]["errno"], 10054)
        self.assertEqual(events[0]["request_id"], "test-request-42")
        self.assertEqual(events[0]["call_id"], events[1]["call_id"])
        self.assertEqual(events[1]["outcome"], "recovered")
        self.assertEqual(events[1]["route"], "direct")
        # Production factory must actually persist this event, not only tests' callbacks.
        from agent_core import main as core
        with patch.object(core, "LLM_PROVIDER", "deepseek"), \
             patch.object(core, "_provider_config", return_value=(p.base_url, p.model, p.api_key)), \
             patch.dict("os.environ", {"LLM_PROXY_MODE": "auto"}), \
             patch.object(core.memory, "add_event") as record:
            built = core.build_provider()
            built._request = Mock(return_value=reply())
            self.assertEqual(await built.complete([]), "recovered")
            self.assertEqual(record.call_args.args[0], "provider.transport")
            self.assertEqual(record.call_args.args[1]["route"], "direct")
            self.assertEqual(record.call_args.args[1]["outcome"], "ok")

    async def test_telemetry_failure_cannot_break_good_model_response(self):
        p = provider(on_transport_event=Mock(side_effect=OSError("fixture logger failed")))
        p._request = Mock(return_value=reply())
        with self.assertLogs("agent_core.provider_http", level="WARNING"):
            self.assertEqual(await p.complete([]), "recovered")

    async def test_changed_host_does_not_send_new_credential_to_old_host(self):
        p = provider(reload_config=lambda: ("https://other.invalid", "test-model", "other-secret"))
        p._request = Mock(side_effect=urllib.error.HTTPError(p.completion_url, 401, "no", {}, io.BytesIO(b"{}")))
        with self.assertRaises(ProviderError):
            await p.complete([])
        self.assertEqual(p.api_key, "synthetic-secret")
        self.assertEqual(p._request.call_count, 1)

    async def test_timeout_storm_has_bounded_active_workers(self):
        p = provider()
        p.timeout_seconds = .06
        release = threading.Event()
        lock = threading.Lock()
        started = []
        def slow(_):
            with lock:
                started.append(1)
            release.wait(2)
            return reply()
        p._request = slow
        try:
            results = await asyncio.gather(*(p.complete([]) for _ in range(12)), return_exceptions=True)
            self.assertTrue(all(isinstance(x, ProviderError) for x in results))
            self.assertEqual(len(started), 2)
        finally:
            release.set()
            await asyncio.sleep(.08)
        p._request = Mock(return_value=reply())
        self.assertEqual(await p.complete([]), "recovered")

    async def test_route_policy_is_exact_and_override_is_explicit(self):
        self.assertEqual(route_for("https://chatapi.weixin.qq.com.evil.test", "auto"), "system")
        self.assertEqual(route_for("https://api.example.com", "auto"), "system")
        self.assertEqual(route_for("https://chatapi.weixin.qq.com", "system"), "system")
        self.assertEqual(route_for("http://localhost:1", "system"), "direct")
        self.assertEqual(route_for("https://api.example.com", "direct"), "direct")
        with self.assertRaises(ValueError):
            route_for("https://api.example.com", "typo")

    async def test_invalid_retry_after_and_error_classification(self):
        for value in ("nan", "inf", "bad"):
            err = urllib.error.HTTPError("https://example.test", 429, "busy", {"Retry-After": value}, io.BytesIO())
            self.assertIsNone(retry_delay(err, 1))
        self.assertEqual(category(urllib.error.URLError(TimeoutError())), "timeout")


def tool_reply():
    return json.dumps({"choices": [{"message": {"role": "assistant", "content": None,
        "tool_calls": [{"id": "call_1", "type": "function", "function": {
            "name": "test_write", "arguments": "{}"}}]}}]}).encode()


class LocalWireFaultTests(unittest.IsolatedAsyncioTestCase):
    """Actual sockets on an ephemeral loopback port; never the desktop Core."""
    async def asyncSetUp(self):
        self.actions = []
        self.bodies = []
        owner = self
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass
            def do_POST(self):
                owner.bodies.append(self.rfile.read(int(self.headers.get("Content-Length", 0))))
                action = owner.actions.pop(0) if owner.actions else "ok"
                if action == "reset":
                    self.connection.shutdown(socket.SHUT_RDWR)
                    self.connection.close()
                    return
                if action == "slow":
                    time.sleep(.25)
                if action == "trickle":
                    self.send_response(200)
                    self.send_header("Content-Length", "1000")
                    self.end_headers()
                    try:
                        for _ in range(100):
                            self.wfile.write(b" ")
                            self.wfile.flush()
                            time.sleep(.01)
                    except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                        pass
                    self.close_connection = True
                    return
                data = reply("wire recovered")
                self.send_response(503 if action == "503" else 200)
                self.send_header("Content-Length", str(len(data) + (10 if action == "partial" else 0)))
                self.end_headers()
                try:
                    self.wfile.write(data)
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    pass
                self.close_connection = True
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.worker = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": .02}, daemon=True)
        self.worker.start()
        self.p = provider()
        self.p.base_url = f"http://127.0.0.1:{self.server.server_port}/v1"

    async def asyncTearDown(self):
        await asyncio.to_thread(self.server.shutdown)
        self.server.server_close()
        self.worker.join(1)

    async def test_real_socket_reset_then_recovery(self):
        self.actions = ["reset", "ok"]
        self.assertEqual(await self.p.complete([]), "wire recovered")
        self.assertEqual(len(self.bodies), 2)

    async def test_real_socket_gateway_retry(self):
        self.actions = ["503", "ok"]
        self.assertEqual(await self.p.complete_with_tools([], []),
                         {"content": "wire recovered", "tool_calls": [], "raw": {"content": "wire recovered"}})
        self.assertEqual(self.bodies[0], self.bodies[1])

    async def test_real_socket_partial_body_then_recovery(self):
        self.actions = ["partial", "ok"]
        self.assertEqual(await self.p.complete([]), "wire recovered")
        self.assertEqual(len(self.bodies), 2)

    async def test_real_socket_slow_response_is_bounded_and_next_request_works(self):
        self.actions = ["slow", "ok"]
        self.p.timeout_seconds = .06
        with self.assertRaisesRegex(ProviderError, "超时"):
            await self.p.complete([])
        self.p.timeout_seconds = 2
        self.assertEqual(await self.p.complete([]), "wire recovered")

    async def test_real_socket_bad_system_proxy_does_not_affect_local_route(self):
        with patch("urllib.request.getproxies", return_value={"http": "http://127.0.0.1:1"}):
            self.assertEqual(await self.p.complete([]), "wire recovered")

    async def test_real_socket_persistent_outage_then_next_turn_recovers(self):
        self.actions = ["503"] * 3 + ["ok"]
        with self.assertRaises(ProviderError):
            await self.p.complete([])
        self.assertEqual(len(self.bodies), 3)
        self.assertEqual(await self.p.complete([]), "wire recovered")

    async def test_real_socket_trickling_body_releases_worker_after_deadline(self):
        self.actions = ["trickle", "ok"]
        self.p.timeout_seconds = .06
        with self.assertRaisesRegex(ProviderError, "超时"):
            await self.p.complete([])
        await asyncio.sleep(.15)
        self.assertEqual(self.p._transport._slots._value, 2)
        self.p.timeout_seconds = 2
        self.assertEqual(await self.p.complete([]), "wire recovered")
