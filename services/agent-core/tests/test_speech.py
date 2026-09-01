from __future__ import annotations

import asyncio
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from agent_core.speech import (
    SpeechClient,
    SpeechManager,
    SpeechUnavailable,
    speech_settings_from_env,
)


class _Handler(BaseHTTPRequestHandler):
    def _send(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path.startswith("/health"):
            self._send({"ok": True, "device": "cuda"})
        else:
            self._send({"ok": False, "error": "not found"}, 404)

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length).decode("utf-8"))
        if self.path.startswith("/synthesize"):
            self._send({
                "ok": True,
                "audioPath": "C:/spool/utt_test.wav",
                "durationMs": 1,
                "sampleRate": 32000,
            })
        else:
            self._send({"ok": False, "error": "not found"}, 404)

    def log_message(self, fmt: str, *args) -> None:
        pass


def _start_server() -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def _stop_server(server: ThreadingHTTPServer) -> None:
    server.shutdown()
    server.server_close()


class SpeechClientHttpTests(unittest.TestCase):
    def test_synthesize_roundtrip_and_health(self) -> None:
        server = _start_server()
        self.addCleanup(_stop_server, server)
        port = server.server_address[1]
        client = SpeechClient(f"http://127.0.0.1:{port}")
        self.assertTrue(client.probe_health())
        result = client.synthesize("你好")
        self.assertEqual(result["durationMs"], 1)
        self.assertEqual(result["sampleRate"], 32000)
        self.assertTrue(result["audioPath"].endswith(".wav"))

    def test_unreachable_service_raises_unavailable(self) -> None:
        client = SpeechClient("http://127.0.0.1:9", health_timeout=0.5, synth_timeout=1.0)
        with self.assertRaises(SpeechUnavailable):
            client.synthesize("你好")
        self.assertFalse(client.is_healthy())


class _FakeClient:
    def __init__(self, fail: bool = False) -> None:
        self.calls: list[str] = []
        self.fail = fail

    def synthesize(self, text: str, speed: float = 1.0) -> dict:
        self.calls.append(text)
        if self.fail:
            raise SpeechUnavailable("sidecar down")
        return {"audioPath": "C:/spool/utt_fake.wav", "durationMs": 1, "sampleRate": 32000}


class SpeechManagerTests(unittest.IsolatedAsyncioTestCase):
    def _manager(self, client, grace: float = 0.05):
        events: list[tuple] = []

        async def on_speak(payload) -> None:
            events.append(("speak", payload["utteranceId"], payload["audioPath"]))

        async def on_interrupt(utterance_id: str, reason: str) -> None:
            events.append(("stop", utterance_id, reason))

        mgr = SpeechManager(
            client,
            on_speak=on_speak,
            on_interrupt=on_interrupt,
            completion_grace_seconds=grace,
        )
        return mgr, events

    async def test_speak_happy_path(self) -> None:
        mgr, events = self._manager(_FakeClient())
        utt = await mgr.speak("你好", "req-1")
        self.assertEqual(events[0][0], "speak")
        self.assertTrue(utt.has_audio and not utt.cancelled)
        self.assertIsNone(mgr.current)
        self.assertTrue(utt.done.is_set())

    async def test_synth_failure_raises_and_clears(self) -> None:
        mgr, events = self._manager(_FakeClient(fail=True))
        with self.assertRaises(SpeechUnavailable):
            await mgr.speak("你好", "req-1")
        self.assertEqual(events, [])
        self.assertIsNone(mgr.current)

    async def test_interrupt_idle_is_noop(self) -> None:
        mgr, _events = self._manager(_FakeClient())
        self.assertFalse(await mgr.interrupt("voice"))

    async def _wait_has_audio(self, mgr) -> None:
        while mgr.current is None or not mgr.current.has_audio:
            await asyncio.sleep(0.005)
        assert mgr.current is not None

    async def test_interrupt_while_playing(self) -> None:
        mgr, events = self._manager(_FakeClient())
        task = asyncio.create_task(mgr.speak("你好", "req-1"))
        await self._wait_has_audio(mgr)
        self.assertTrue(await mgr.interrupt("voice"))
        utt = await task
        self.assertTrue(utt.cancelled)
        self.assertEqual(events, [
            ("speak", utt.id, "C:/spool/utt_fake.wav"),
            ("stop", utt.id, "voice"),
        ])
        self.assertIsNone(mgr.current)

    async def test_new_speak_supersedes_current(self) -> None:
        mgr, events = self._manager(_FakeClient())
        t1 = asyncio.create_task(mgr.speak("第一句", "r1"))
        await self._wait_has_audio(mgr)
        t2 = asyncio.create_task(mgr.speak("第二句", "r2"))
        await self._wait_has_audio(mgr)
        utt1 = await t1
        utt2 = await t2
        self.assertTrue(utt1.cancelled)
        self.assertFalse(utt2.cancelled)
        self.assertEqual(events[-1][0], "speak")
        stop_events = [e for e in events if e[0] == "stop"]
        self.assertEqual(len(stop_events), 1)
        self.assertEqual(stop_events[0][2], "superseded")
        self.assertIsNone(mgr.current)

    async def test_notify_finished_resolves_wait(self) -> None:
        mgr, events = self._manager(_FakeClient())
        task = asyncio.create_task(mgr.speak("你好", "req-1"))
        await self._wait_has_audio(mgr)
        utt = mgr.current
        assert utt is not None
        self.assertTrue(await mgr.notify_finished(utt.id))
        result = await task
        self.assertFalse(result.cancelled)
        self.assertIsNone(mgr.current)


class SpeechSettingsTests(unittest.TestCase):
    def test_defaults_are_off(self) -> None:
        settings = speech_settings_from_env({})
        self.assertFalse(settings["enabled"])
        self.assertTrue(settings["narrate"])
        self.assertEqual(settings["url"], "http://127.0.0.1:8770")

    def test_env_overrides(self) -> None:
        settings = speech_settings_from_env({
            "ANIME_AGENT_TTS": "1",
            "ANIME_AGENT_TTS_NARRATE": "0",
            "TTS_SERVICE_URL": "http://127.0.0.1:9999",
        })
        self.assertTrue(settings["enabled"])
        self.assertFalse(settings["narrate"])
        self.assertEqual(settings["url"], "http://127.0.0.1:9999")


if __name__ == "__main__":
    unittest.main()
