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
            payload = _post_json(f"{self.base_url}/synthesize", {"text": text, "speed": speed}, self.synth_timeout)
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
            return {
                "audioPath": str(payload["audioPath"]),
                "durationMs": int(payload["durationMs"]),
                "sampleRate": int(payload["sampleRate"]),
            }
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
            utterance = self._current
            if utterance is None or utterance.cancelled:
                return False
            utterance.cancelled = True
            utterance.cancel_event.set()
            if utterance.has_audio:
                await self.on_interrupt(utterance.id, reason)
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
        await self.interrupt("superseded")
        parts = [text] if prepared_audio is not None else (split_reply_into_parts(text) or [text])
        utterance = Utterance(id=self.new_utterance_id(), text=text, request_id=request_id)
        async with self._lock:
            self._current = utterance
        try:
            audio = prepared_audio or await self._synthesize_with_recovery(utterance, parts[0])
            if audio is None:
                return utterance
            utterance.has_audio = True
            index = 0
            while True:
                playback = asyncio.create_task(self._play_part(utterance, parts[index], audio, index, len(parts)))
                next_audio = None
                next_error = None
                try:
                    if index + 1 < len(parts):
                        try:
                            next_audio = await self._synthesize_with_recovery(utterance, parts[index + 1])
                        except SpeechUnavailable as exc:
                            # Keep ownership until the playing part settles.
                            next_error = exc
                    await playback
                finally:
                    if not playback.done():
                        playback.cancel()
                    await asyncio.gather(playback, return_exceptions=True)
                if utterance.cancelled:
                    break
                if next_error is not None:
                    raise next_error
                if next_audio is None:
                    utterance.completed = True
                    break
                index += 1
                audio = next_audio
        finally:
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
                audio = await self._synthesize_with_recovery(utterance, text)
                if audio is None:
                    return
                utterance.playback_id = uuid.uuid4().hex
                utterance.playback_error = ""
                utterance.done = asyncio.Event()
        await self.on_interrupt(utterance.id, "playback-failed")
        raise SpeechUnavailable("语音播放未完成：播放器未确认或音频加载失败；请检查声音输出设备")

    async def _synthesize_with_recovery(self, utterance: Utterance, text: str) -> dict | None:
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
            synthesis = asyncio.create_task(asyncio.to_thread(self.client.synthesize, text, self.speed))
            cancellation = asyncio.create_task(utterance.cancel_event.wait())
            try:
                done, _ = await asyncio.wait({synthesis, cancellation}, timeout=remaining,
                                            return_when=asyncio.FIRST_COMPLETED)
                if utterance.cancelled or self._current is not utterance:
                    return None
                if synthesis not in done:
                    raise SpeechUnavailable("语音服务恢复超时，文字回复已保留，请稍后重试")
                audio = synthesis.result()
                if notified:
                    logger.info("TTS recovered utterance=%s", utterance.id)
                return audio
            except SpeechUnavailable as exc:
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
