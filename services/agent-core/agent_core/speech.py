"""TTS speech pipeline (Phase E): sidecar client + interruption-aware speech manager.

The GPT-SoVITS voice lives in an out-of-repo sidecar (see docs/LOCAL_DEV.md);
this module is deliberately dependency-free (urllib only) so the Core venv
never needs torch. Every failure mode degrades to SpeechUnavailable and the
caller falls back to the pre-E-phase text-only flow.
"""

from __future__ import annotations

import asyncio
import http.client
import json
import logging
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from dataclasses import dataclass, field


STRONG_PUNCTUATION = "。！？；…!?" + chr(10)
WEAK_PUNCTUATION = "，、：,:"
PART_MAX_CHARS = 48
logger = logging.getLogger(__name__)


def split_reply_into_parts(text: str, max_chars: int = PART_MAX_CHARS) -> list[str]:
    """Split a reply into speakable parts, strongest punctuation first.

    Sentence ends (。！？；…) always break; chunks longer than max_chars
    are repacked at weaker punctuation (，、：) and hard-wrapped as a last
    resort. Punctuation stays attached so each part keeps its natural cadence.
    """
    chunks: list[str] = []
    buffer = ""
    for char in text:
        buffer += char
        if char in STRONG_PUNCTUATION:
            chunks.append(buffer)
            buffer = ""
    if buffer:
        chunks.append(buffer)

    parts: list[str] = []
    for chunk in chunks:
        if len(chunk) <= max_chars:
            parts.append(chunk)
            continue
        current = ""
        for token in _split_weak(chunk):
            while len(token) > max_chars:
                if current:
                    parts.append(current)
                    current = ""
                parts.append(token[:max_chars])
                token = token[max_chars:]
            if current and len(current) + len(token) > max_chars:
                parts.append(current)
                current = token
            else:
                current += token
        if current:
            parts.append(current)
    cleaned = [part.strip() for part in parts]
    return [part for part in cleaned if part]


def _split_weak(chunk: str) -> list[str]:
    tokens: list[str] = []
    buffer = ""
    for char in chunk:
        buffer += char
        if char in WEAK_PUNCTUATION:
            tokens.append(buffer)
            buffer = ""
    if buffer:
        tokens.append(buffer)
    return tokens


class SpeechUnavailable(RuntimeError):
    """The TTS sidecar is unreachable, unhealthy, or refused the synthesis."""

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


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
        """Probe availability; a negative result is cached for at most 2s."""
        try:
            payload = _get_json(self.health_url, self.health_timeout)
            healthy = isinstance(payload, dict) and payload.get("ok") is True
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError, ValueError):
            healthy = False
        if self._healthy != healthy:
            logger.info("TTS availability=%s", healthy)
        self._healthy = healthy
        self._probed_monotonic = time.monotonic()
        return healthy

    def is_healthy(self, max_age: float = 60.0) -> bool:
        # Codex: either cache direction expires within 2s. A previously healthy
        # sidecar may have restarted into model warming; a 60s positive cache
        # falsely reported readiness and dropped the first post-recovery reply.
        max_age = min(max_age, 2.0)
        if self._healthy is not None and time.monotonic() - self._probed_monotonic < max_age:
            return self._healthy
        return self.probe_health()

    def invalidate_health(self) -> None:
        self._healthy = None

    def synthesize(self, text: str, speed: float = 1.0) -> dict:
        """Returns {"audioPath", "durationMs", "sampleRate"}; raises SpeechUnavailable."""
        try:
            payload = _post_json(f"{self.base_url}/synthesize",
                                 {"text": text, "speed": speed, "includeTakeTiming": True}, self.synth_timeout)
        except urllib.error.HTTPError as exc:
            self.invalidate_health()
            # Codex: warming/busy/crashed inference is recoverable; bad input
            # and authentication are not. Never log response bodies or text.
            retryable = exc.code in {408, 429, 500, 502, 503, 504}
            try:
                detail = json.loads(exc.read(8192))
                if (isinstance(detail, dict) and detail.get("error_type") in {"encoding", "invalid_input"}
                        and detail.get("retryable") is False):
                    retryable = False
            except (ValueError, TypeError, OSError, http.client.HTTPException):
                pass  # Older sidecars keep their bounded status-code recovery.
            logger.warning("TTS synthesis HTTP %s (retryable=%s)", exc.code, retryable)
            raise SpeechUnavailable(f"TTS 服务暂不可用（HTTP {exc.code}）", retryable=retryable) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            self.invalidate_health()
            logger.warning("TTS synthesis unavailable (%s)", type(exc).__name__)
            raise SpeechUnavailable("TTS 服务暂时无法连接", retryable=True) from exc
        except json.JSONDecodeError as exc:
            self.invalidate_health()
            raise SpeechUnavailable("TTS 服务响应格式无法识别") from exc
        if not isinstance(payload, dict):
            self.invalidate_health()
            raise SpeechUnavailable("TTS 服务响应格式无法识别")
        if payload.get("ok") is not True:
            self.invalidate_health()
            raise SpeechUnavailable(str(payload.get("error", "TTS 合成失败"))[:200])
        try:
            audio = {
                "audioPath": str(payload["audioPath"]),
                "durationMs": int(payload["durationMs"]),
                "sampleRate": int(payload["sampleRate"]),
            }
            timing = payload.get("takeTiming")
            if isinstance(timing, dict) and isinstance(timing.get("takes"), list):
                fields = ("take", "synthStartMs", "synthEndMs", "checkStartMs", "checkEndMs")
                audio["takeTiming"] = {
                    **{k: timing[k] for k in ("selectedTake", "selectedAtMs") if type(timing.get(k)) is int},
                    "takes": [{k: t[k] for k in fields if type(t.get(k)) is int}
                              for t in timing["takes"][:16] if isinstance(t, dict)],
                }
            return audio
        except (KeyError, TypeError, ValueError) as exc:
            self.invalidate_health()
            raise SpeechUnavailable("TTS 服务响应缺少字段") from exc


@dataclass(slots=True)
class Utterance:
    id: str
    text: str
    request_id: str
    cancelled: bool = False
    has_audio: bool = False
    completed: bool = False
    playback_id: str = ""
    playback_error: str = ""
    done: asyncio.Event = field(default_factory=asyncio.Event)
    cancel_event: asyncio.Event = field(default_factory=asyncio.Event)
    needed_part: int = 0


@dataclass(slots=True, eq=False)
class _SynthesisWaiter:
    utterance: Utterance | None
    index: int
    turn: asyncio.Future

    @property
    def priority(self) -> int:
        if self.utterance is None:
            return 2  # Farewell cache.
        return 0 if self.index == self.utterance.needed_part else 1


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
        recovery_timeout_seconds: float = 180.0,
        retry_interval_seconds: float = 1.0,
        on_recovery=None,
        playback_attempts: int = 3,
        lookahead: int = 1,
        on_timing=None,
    ) -> None:
        self.client = client
        self.on_speak = on_speak  # async (utterance dict) -> None, broadcast to avatar
        self.on_interrupt = on_interrupt  # async (utterance_id, reason) -> None
        self.speed = speed
        self.completion_grace_seconds = completion_grace_seconds
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self.retry_interval_seconds = retry_interval_seconds
        self.on_recovery = on_recovery
        self.playback_attempts = playback_attempts
        self.lookahead = min(2, max(1, lookahead))
        self.on_timing = on_timing
        self._synthesis_waiters: list[_SynthesisWaiter] = []
        self._synthesis_worker: asyncio.Future | None = None
        self._synth_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="tts-synth")
        self._current: Utterance | None = None
        self._lock = asyncio.Lock()

    @property
    def current(self) -> Utterance | None:
        return self._current

    @staticmethod
    def new_utterance_id() -> str:
        return "utt-" + uuid.uuid4().hex[:12]

    async def _finish(self, utterance: Utterance) -> None:
        utterance.done.set()

    async def interrupt(self, reason: str) -> bool:
        async with self._lock:
            return await self._interrupt_current_locked(reason)

    async def _interrupt_current_locked(self, reason: str) -> bool:
        utterance = self._current
        if utterance is None or utterance.cancelled:
            return False
        utterance.cancelled = True
        utterance.cancel_event.set()
        try:
            if utterance.has_audio:
                await self.on_interrupt(utterance.id, reason)
        finally:
            await self._finish(utterance)
        return True

    async def speak(self, text: str, request_id: str = "", *, prepared_audio: dict | None = None) -> Utterance:
        """Synthesize and broadcast one utterance; resolves when playback is
        acknowledged complete or interrupted; timeout is a failure, not success.

        Long replies are split at sentence punctuation and streamed part by
        part: each avatar.speak goes out as soon as the previous part's
        playback finishes, so the first sentence is heard after one short
        synthesis instead of the full reply's. All parts share one
        utteranceId; an interrupt stops both playback and further parts.
        """
        parts = [text] if prepared_audio is not None else (split_reply_into_parts(text) or [text])
        utterance = Utterance(id=self.new_utterance_id(), text=text, request_id=request_id)
        async with self._lock:
            await self._interrupt_current_locked("superseded")
            self._current = utterance
        pending = deque()
        try:
            audio = prepared_audio or await self._synthesize_with_recovery(utterance, parts[0], 0)
            for index, part in enumerate(parts):
                if index:
                    # Promote the original preparation, including any recovery attempt.
                    utterance.needed_part = index
                    self._wake_next_synthesis()
                    audio = await pending.popleft()
                if audio is None or utterance.cancelled or self._current is not utterance:
                    return utterance
                utterance.has_audio = True
                # Only paths and metadata are retained here. Godot loads one WAV at a time.
                while len(pending) < self.lookahead and index + len(pending) + 1 < len(parts):
                    ahead = index + len(pending) + 1
                    pending.append(asyncio.create_task(self._synthesize_with_recovery(utterance, parts[ahead], ahead)))
                await self._play_part(utterance, part, audio, index, len(parts))
                if utterance.cancelled:
                    return utterance
            utterance.completed = True
        finally:
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
            await self._finish(utterance)
            async with self._lock:
                if self._current is utterance:
                    self._current = None
        return utterance

    async def _play_part(self, utterance: Utterance, text: str, audio: dict, index: int, count: int) -> None:
        # Codex: retry delivery with the SAME id. The Avatar deduplicates it and
        # re-sends its receipt, so a lost ack cannot replay an already heard line.
        # Only an explicit unplayed/load failure permits synthesis of a new file.
        utterance.playback_id = uuid.uuid4().hex
        utterance.playback_error = ""
        utterance.done = asyncio.Event()
        for attempt in range(self.playback_attempts):
            if utterance.cancelled or self._current is not utterance:
                return
            self._timing(utterance, index, "dispatch", playbackId=utterance.playback_id,
                         preparationId=audio.get("preparationId"),
                         selectedTake=audio.get("takeTiming", {}).get("selectedTake"))
            await self.on_speak(self._part_payload(utterance, text, audio, index, count))
            try:
                await asyncio.wait_for(utterance.done.wait(),
                    max(0.001, audio["durationMs"] / 1000.0 + self.completion_grace_seconds))
            except asyncio.TimeoutError:
                logger.warning("Speech receipt missing utterance=%s part=%s attempt=%s", utterance.id, index, attempt + 1)
                continue
            if utterance.cancelled:
                return
            if not utterance.playback_error:
                return
            if attempt + 1 < self.playback_attempts:
                audio = await self._synthesize_with_recovery(utterance, text, index)
                if audio is None:
                    return
                utterance.playback_id = uuid.uuid4().hex
                utterance.playback_error = ""
                utterance.done = asyncio.Event()
        await self.on_interrupt(utterance.id, "playback-failed")
        raise SpeechUnavailable("语音播放未完成：播放器未确认或音频加载失败；请检查声音输出设备")

    def _timing(self, utterance, index, stage, **fields):
        if self.on_timing:
            try:
                self.on_timing(dict(requestId=utterance.request_id, utteranceId=utterance.id, partIndex=index,
                                    stage=stage, atMs=time.time_ns() // 1_000_000, **fields))
            except Exception:
                logger.warning("Speech timing sink unavailable")

    def _next_synthesis(self):
        # min is stable. This list contains at most the bounded lookahead,
        # foreground requests and the one session-owned farewell preparation.
        return min(self._synthesis_waiters, key=lambda waiter: waiter.priority, default=None)

    def _wake_next_synthesis(self):
        if self._synthesis_worker is None:
            head = self._next_synthesis()
            if head is not None and not head.turn.done():
                head.turn.set_result(None)

    def _synthesis_returned(self, worker):
        # The caller can go away during HTTP. Only the actual return frees this slot.
        if not worker.cancelled():
            worker.exception()
        self._synthesis_worker = None
        self._wake_next_synthesis()

    async def prepare_farewell(self, text: str) -> dict:
        return await self._serial_synth(None, -1, text, "")

    async def _serial_synth(self, utterance, index, text, preparation_id):
        loop = asyncio.get_running_loop()
        waiter = _SynthesisWaiter(utterance, index, loop.create_future())
        enqueued = time.monotonic_ns()
        initial_priority = waiter.priority
        self._synthesis_waiters.append(waiter)
        try:
            while True:
                self._wake_next_synthesis()
                await waiter.turn
                if utterance is not None and (utterance.cancelled or self._current is not utterance):
                    return None
                # A wakeup is not a reservation. Recheck after cancellation,
                # promotion or a higher-priority arrival in the same loop turn.
                if self._synthesis_worker is None and self._next_synthesis() is waiter:
                    break
                waiter.turn = loop.create_future()
            self._synthesis_waiters.remove(waiter)
            waited_ms = (time.monotonic_ns() - enqueued) / 1_000_000
            worker = loop.run_in_executor(self._synth_executor, copy_context().run,
                                          self.client.synthesize, text, self.speed)
            self._synthesis_worker = worker
            worker.add_done_callback(self._synthesis_returned)
            if utterance is not None:
                self._timing(utterance, index, "synth-request", preparationId=preparation_id,
                             queuedPriority=initial_priority, priority=waiter.priority, queueWaitMs=round(waited_ms, 3))
            return await asyncio.shield(worker)
        finally:
            if waiter in self._synthesis_waiters:
                self._synthesis_waiters.remove(waiter)
            self._wake_next_synthesis()

    async def _synthesize_with_recovery(self, utterance: Utterance, text: str, index: int) -> dict | None:
        """Codex: retry only unplayed audio, with a deadline and cancellation.

        An HTTP request may outlive its asyncio task; it may finish generating
        a spool file, but a superseded generation can never reach the avatar.
        Playback acknowledgements are NOT cancellation signals between parts.
        """
        deadline = time.monotonic() + self.recovery_timeout_seconds
        notified = False
        while not utterance.cancelled and self._current is utterance:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise SpeechUnavailable("语音服务恢复超时，文字回复已保留，请稍后重试")
            preparation_id = uuid.uuid4().hex
            synthesis = asyncio.create_task(self._serial_synth(utterance, index, text, preparation_id))
            cancellation = asyncio.create_task(utterance.cancel_event.wait())
            try:
                done, _ = await asyncio.wait({synthesis, cancellation}, timeout=remaining,
                                            return_when=asyncio.FIRST_COMPLETED)
                if utterance.cancelled or self._current is not utterance:
                    return None
                if synthesis not in done:
                    raise SpeechUnavailable("语音服务恢复超时，文字回复已保留，请稍后重试")
                audio = dict(synthesis.result(), preparationId=preparation_id)
                self._timing(utterance, index, "ready", preparationId=preparation_id, **audio.get("takeTiming", {}))
                if notified:
                    logger.info("TTS recovered utterance=%s", utterance.id)
                return audio
            except SpeechUnavailable as exc:
                self._timing(utterance, index, "synth-failed", preparationId=preparation_id, retryable=exc.retryable)
                if not exc.retryable:
                    raise
                if not notified:
                    notified = True
                    logger.warning("TTS waiting for recovery utterance=%s", utterance.id)
                    if self.on_recovery is not None:
                        await self.on_recovery(utterance.id, utterance.request_id)
            finally:
                for task in (synthesis, cancellation):
                    if not task.done():
                        task.cancel()
                await asyncio.gather(synthesis, cancellation, return_exceptions=True)
            try:
                await asyncio.wait_for(utterance.cancel_event.wait(),
                                       max(0.001, min(self.retry_interval_seconds, deadline - time.monotonic())))
            except asyncio.TimeoutError:
                pass
        return None

    @staticmethod
    def _part_payload(utterance: Utterance, text: str, audio: dict, index: int, count: int) -> dict:
        return {
            "utteranceId": utterance.id,
            "playbackId": utterance.playback_id,
            "text": text,
            "audioPath": audio["audioPath"],
            "durationMs": audio["durationMs"],
            "sampleRate": audio["sampleRate"],
            "requestId": utterance.request_id,
            "partIndex": index,
            "partCount": count,
        }

    async def notify_finished(self, utterance_id: str, playback_id: str | None = None,
                              *, interrupted: bool = False, error: str = "") -> bool:
        """Only a matching part receipt settles it; an interruption isn't success.

        id-only calls remain available to in-process legacy callers. The WS
        boundary requires playbackId and the Avatar role for production frames.
        """
        utterance = self._current
        if (utterance is None or utterance.id != utterance_id or utterance.done.is_set()
                or (error and error != "audio-load-failed" and not interrupted)
                or (playback_id is not None and playback_id != utterance.playback_id)):
            return False
        if interrupted:
            utterance.cancelled = True
            utterance.cancel_event.set()
        utterance.playback_error = error
        await self._finish(utterance)
        return True


def speech_settings_from_env(environ=None) -> dict:
    env = environ if environ is not None else os.environ
    enabled = env.get("ANIME_AGENT_TTS", "0").strip().lower() not in {"0", "false", "off"}
    narrate = env.get("ANIME_AGENT_TTS_NARRATE", "1").strip().lower() not in {"0", "false", "off"}
    url = env.get("TTS_SERVICE_URL", "http://127.0.0.1:8770").strip() or "http://127.0.0.1:8770"
    return {"enabled": enabled, "narrate": narrate, "url": url}
