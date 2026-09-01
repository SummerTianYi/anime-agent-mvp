"""TTS speech pipeline (Phase E): sidecar client + interruption-aware speech manager.

The GPT-SoVITS voice lives in an out-of-repo sidecar (see docs/LOCAL_DEV.md);
this module is deliberately dependency-free (urllib only) so the Core venv
never needs torch. Every failure mode degrades to SpeechUnavailable and the
caller falls back to the pre-E-phase text-only flow.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass, field


class SpeechUnavailable(RuntimeError):
    """The TTS sidecar is unreachable, unhealthy, or refused the synthesis."""


def _post_json(url: str, payload: dict, timeout: float) -> dict:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        method="POST",
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _get_json(url: str, timeout: float) -> dict:
    request = urllib.request.Request(url, headers={"Accept": "application/json"}, method="GET")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


class SpeechClient:
    def __init__(self, base_url: str, health_timeout: float = 2.0, synth_timeout: float = 90.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.health_timeout = health_timeout
        self.synth_timeout = synth_timeout
        self._healthy: bool | None = None
        self._probed_monotonic: float = 0.0

    @property
    def health_url(self) -> str:
        return f"{self.base_url}/health"

    def probe_health(self) -> bool:
        """Force a health probe; caches the result for 60 seconds."""
        try:
            payload = _get_json(self.health_url, self.health_timeout)
            healthy = bool(payload.get("ok"))
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError, ValueError):
            healthy = False
        self._healthy = healthy
        self._probed_monotonic = time.monotonic()
        return healthy

    def is_healthy(self, max_age: float = 60.0) -> bool:
        if self._healthy is not None and time.monotonic() - self._probed_monotonic < max_age:
            return self._healthy
        return self.probe_health()

    def invalidate_health(self) -> None:
        self._healthy = None

    def synthesize(self, text: str, speed: float = 1.0) -> dict:
        """Returns {"audioPath", "durationMs", "sampleRate"}; raises SpeechUnavailable."""
        try:
            payload = _post_json(f"{self.base_url}/synthesize", {"text": text, "speed": speed}, self.synth_timeout)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            self.invalidate_health()
            raise SpeechUnavailable(f"TTS 服务不可达：{exc}") from exc
        except json.JSONDecodeError as exc:
            raise SpeechUnavailable("TTS 服务响应格式无法识别") from exc
        if not payload.get("ok"):
            self.invalidate_health()
            raise SpeechUnavailable(str(payload.get("error", "TTS 合成失败"))[:200])
        try:
            return {
                "audioPath": str(payload["audioPath"]),
                "durationMs": int(payload["durationMs"]),
                "sampleRate": int(payload["sampleRate"]),
            }
        except (KeyError, TypeError, ValueError) as exc:
            raise SpeechUnavailable("TTS 服务响应缺少字段") from exc


@dataclass(slots=True)
class Utterance:
    id: str
    text: str
    request_id: str
    cancelled: bool = False
    has_audio: bool = False
    done: asyncio.Future = field(default_factory=lambda: asyncio.get_event_loop().create_future())


class SpeechManager:
    """Owns the single current utterance and the interruption policy.

    interrupt() marks the active utterance cancelled, notifies the avatar via
    on_interrupt, and releases the waiter. A superseding speak() interrupts the
    previous utterance automatically, so a new chat message barges in without
    the caller caring about speech state.
    """

    def __init__(
        self,
        client: SpeechClient,
        on_speak,
        on_interrupt,
        speed: float = 1.0,
        completion_grace_seconds: float = 5.0,
    ) -> None:
        self.client = client
        self.on_speak = on_speak  # async (utterance dict) -> None, broadcast to avatar
        self.on_interrupt = on_interrupt  # async (utterance_id, reason) -> None
        self.speed = speed
        self.completion_grace_seconds = completion_grace_seconds
        self._current: Utterance | None = None
        self._lock = asyncio.Lock()

    @property
    def current(self) -> Utterance | None:
        return self._current

    @staticmethod
    def new_utterance_id() -> str:
        return "utt-" + uuid.uuid4().hex[:12]

    async def _finish(self, utterance: Utterance) -> None:
        if not utterance.done.done():
            utterance.done.set_result(None)

    async def interrupt(self, reason: str) -> bool:
        async with self._lock:
            utterance = self._current
            if utterance is None or utterance.done.done():
                return False
            utterance.cancelled = True
            if utterance.has_audio:
                await self.on_interrupt(utterance.id, reason)
            await self._finish(utterance)
            return True

    async def speak(self, text: str, request_id: str = "") -> Utterance:
        """Synthesize and broadcast one utterance; resolves when playback is
        done (speech.finished), interrupted, or timed out."""
        await self.interrupt("superseded")
        utterance = Utterance(id=self.new_utterance_id(), text=text, request_id=request_id)
        async with self._lock:
            self._current = utterance
        try:
            audio = await asyncio.to_thread(self.client.synthesize, text, self.speed)
        except SpeechUnavailable:
            async with self._lock:
                if self._current is utterance:
                    self._current = None
            await self._finish(utterance)
            raise
        if utterance.cancelled:
            await self._finish(utterance)
            return utterance
        utterance.has_audio = True
        await self.on_speak(
            {
                "utteranceId": utterance.id,
                "text": text,
                "audioPath": audio["audioPath"],
                "durationMs": audio["durationMs"],
                "sampleRate": audio["sampleRate"],
                "requestId": request_id,
            }
        )
        try:
            await asyncio.wait_for(
                utterance.done,
                timeout=audio["durationMs"] / 1000.0 + self.completion_grace_seconds,
            )
        except asyncio.TimeoutError:
            pass
        finally:
            async with self._lock:
                if self._current is utterance:
                    self._current = None
        return utterance

    async def notify_finished(self, utterance_id: str) -> bool:
        """Avatar reports playback ended (naturally or via stop)."""
        utterance = self._current
        if utterance is None or utterance.id != utterance_id:
            return False
        await self._finish(utterance)
        return True


def speech_settings_from_env(environ=None) -> dict:
    env = environ if environ is not None else os.environ
    enabled = env.get("ANIME_AGENT_TTS", "0").strip().lower() not in {"0", "false", "off"}
    narrate = env.get("ANIME_AGENT_TTS_NARRATE", "1").strip().lower() not in {"0", "false", "off"}
    url = env.get("TTS_SERVICE_URL", "http://127.0.0.1:8770").strip() or "http://127.0.0.1:8770"
    return {"enabled": enabled, "narrate": narrate, "url": url}
