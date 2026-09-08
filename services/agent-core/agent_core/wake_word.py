from __future__ import annotations

import io
import re
import threading
import time
from collections import deque
import wave
from pathlib import Path
from typing import Any, Callable

from .voice import VoiceError


def default_kws_model_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "models" / "sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01"


def default_wake_keywords_file() -> Path:
    return Path(__file__).resolve().parent / "data" / "wake_tianyi.txt"


# zcode (2026-09-09, 接手 Claude 未竟修复): 同音容错池按真实误听扩充。
# 事件表实证 whisper 把"天依"转写成"天忆"(x2) 和"便宜"(x2)，故 S1 增加 pian 系、
# S2 增加 yi 系常见变体；打招呼词改为可选（KWS 已先行把关，确认关只验名字）。
WAKE_NAME_PATTERN = re.compile(r"[天填添田甜便片偏篇][^A-Za-z0-9]{0,2}[依一衣仪伊怡忆亦易益艺议翼宜]")
WAKE_GREETING_PATTERN = re.compile(r"嗨|嘿|哎|哈喽|hello", re.IGNORECASE)


def is_wake_phrase(text: str) -> bool:
    """确认转写文本是唤醒口令：名字同音容错（打招呼词可选）。"""
    return bool(WAKE_NAME_PATTERN.search(text))


def _import_audio_dependencies() -> tuple[Any, Any]:
    try:
        import numpy as np
        import sounddevice as sd
    except ImportError as exc:
        raise VoiceError("唤醒依赖尚未安装，请先安装语音依赖与 sherpa-onnx") from exc
    return np, sd


def build_keyword_spotter(
    model_dir: Path | None = None,
    keywords_file: Path | None = None,
    keywords_score: float = 1.0,
    keywords_threshold: float = 0.25,
) -> Any:
    """加载 sherpa-onnx 关键词检出引擎；模型或依赖缺失时抛 VoiceError。"""
    try:
        import sherpa_onnx
    except ImportError as exc:
        raise VoiceError("唤醒词依赖尚未安装（pip install sherpa-onnx）") from exc
    base = model_dir or default_kws_model_dir()
    keywords = keywords_file or default_wake_keywords_file()
    if not base.is_dir():
        raise VoiceError("唤醒词模型目录缺失")
    if not keywords.is_file():
        raise VoiceError("唤醒词配置文件缺失")
    return _load_spotter(sherpa_onnx, base, keywords, keywords_score, keywords_threshold)


def _load_spotter(
    sherpa_onnx: Any,
    base: Path,
    keywords: Path,
    keywords_score: float,
    keywords_threshold: float,
) -> Any:
    stem = "encoder-epoch-12-avg-2-chunk-16-left-64"
    encoder = base / f"{stem}.int8.onnx"
    suffix = ".int8" if encoder.exists() else ""
    try:
        return sherpa_onnx.KeywordSpotter(
            tokens=str(base / "tokens.txt"),
            encoder=str(base / f"{stem}{suffix}.onnx"),
            decoder=str(base / f"decoder-epoch-12-avg-2-chunk-16-left-64{suffix}.onnx"),
            joiner=str(base / f"joiner-epoch-12-avg-2-chunk-16-left-64{suffix}.onnx"),
            keywords_file=str(keywords),
            keywords_score=keywords_score,
            keywords_threshold=keywords_threshold,
            num_threads=1,
        )
    except Exception as exc:
        raise VoiceError("唤醒词模型加载失败") from exc


class WakeWordListener:
    """常驻唤醒词监听：KWS 引擎 + 静音看门狗（驱动假死自愈）。"""

    sample_rate = 16_000
    block_samples = 1_600  # 100ms
    silence_reopen_seconds = 90.0
    device_silence_amplitude = 1e-5
    wake_cooldown_seconds = 3.0
    # zcode (2026-09-09): Realtek "half-wedge" — the long-lived stream's gain
    # degraded 30-100x (fresh stream on the same device measured 0.386 peak
    # while the listener saw 0.005-0.013), slipping under the pure-silence
    # watchdog. AGC normalizes whatever comes in, so gain drift can no longer
    # kill the wake.
    agc_target_rms = 0.05
    agc_max_gain = 50.0

    def __init__(
        self,
        on_detected: Callable[[Any], None],
        on_note: Callable[[str], None] | None = None,
        model_dir: Path | None = None,
        keywords_file: Path | None = None,
    ) -> None:
        self._on_detected = on_detected
        self._on_note = on_note or (lambda _note: None)
        self._model_dir = model_dir
        self._keywords_file = keywords_file
        self._spotter: Any = None
        self._stream: Any = None
        self._mic: Any = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._paused = threading.Event()
        self._numpy: Any = None
        self._sounddevice: Any = None
        self._last_hit_monotonic = 0.0
        self._recent_chunks: deque[Any] = deque(maxlen=60)
        self._recent_peak = 0.0
        self._agc_ema = 0.0

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _apply_agc(self, chunk: Any) -> Any:
        """Software AGC: normalize speech level so device gain drift (the
        half-wedge) cannot starve the KWS. Never attenuates; digital zeros
        stay zeros for the pure-silence watchdog."""
        rms = float(self._numpy.sqrt(self._numpy.mean(chunk**2))) if chunk.size else 0.0
        self._agc_ema = 0.9 * self._agc_ema + 0.1 * rms
        gain = min(max(self.agc_target_rms / max(self._agc_ema, 1e-4), 1.0), self.agc_max_gain)
        return (chunk * gain).clip(-1.0, 1.0)

    @staticmethod
    def _agc_math(chunk: Any, ema: float, target: float = 0.05, max_gain: float = 50.0) -> tuple[Any, float]:
        rms = float(__import__("numpy").sqrt(__import__("numpy").mean(chunk**2))) if chunk.size else 0.0
        ema = 0.9 * ema + 0.1 * rms
        gain = min(max(target / max(ema, 1e-4), 1.0), max_gain)
        return (chunk * gain).clip(-1.0, 1.0), ema

    @property
    def paused(self) -> bool:
        return self._paused.is_set()

    @property
    def recent_peak(self) -> float:
        return round(self._recent_peak, 4)

    def start(self) -> None:
        if self.running:
            return
        self._spotter = build_keyword_spotter(self._model_dir, self._keywords_file)
        self._numpy, self._sounddevice = _import_audio_dependencies()
        self._stop.clear()
        self._paused.clear()
        self._thread = threading.Thread(target=self._run, name="wake-word-listener", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=3.0)
        self._thread = None
        self._close_mic()

    def pause(self) -> None:
        self._paused.set()
        self._close_mic()

    def resume(self) -> None:
        self._paused.clear()

    def _run(self) -> None:
        stream = self._spotter.create_stream()
        silence_since = time.monotonic()
        while not self._stop.is_set():
            if self._paused.is_set():
                time.sleep(0.05)
                continue
            if self._mic is None:
                try:
                    self._open_mic()
                except Exception:
                    self._on_note("mic-open-failed")
                    time.sleep(2.0)
                    continue
            try:
                data, _overflow = self._mic.read(self.block_samples)
            except Exception:
                self._on_note("mic-read-failed")
                self._close_mic()
                time.sleep(0.5)
                continue
            chunk = self._numpy.frombuffer(data, dtype=self._numpy.float32).reshape(-1)
            chunk = self._apply_agc(chunk)
            self._recent_chunks.append(chunk.copy())
            peak = float(self._numpy.max(self._numpy.abs(chunk)))
            self._recent_peak = max(self._recent_peak * 0.95, peak)
            now = time.monotonic()
            if peak > self.device_silence_amplitude:
                silence_since = now
            elif now - silence_since > self.silence_reopen_seconds:
                self._on_note("device-silence-reopened")
                self._close_mic()
                silence_since = now
                continue
            stream.accept_waveform(self.sample_rate, chunk)
            while self._spotter.is_ready(stream):
                self._spotter.decode_stream(stream)
            result = self._spotter.get_result(stream)
            if result:
                self._spotter.reset_stream(stream)
                now_wall = time.monotonic()
                if now_wall - self._last_hit_monotonic >= self.wake_cooldown_seconds:
                    self._last_hit_monotonic = now_wall
                    buffered = self._numpy.concatenate(list(self._recent_chunks), axis=0) if self._recent_chunks else None
                    self._on_detected(buffered)

    def _open_mic(self) -> None:
        mic = self._sounddevice.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            blocksize=self.block_samples,
        )
        mic.start()
        self._mic = mic

    def _close_mic(self) -> None:
        mic, self._mic = self._mic, None
        if mic is not None:
            try:
                mic.stop()
                mic.close()
            except Exception:
                pass


_capture_token_lock = threading.Lock()
_current_capture_token: threading.Event | None = None


def begin_capture_scope() -> threading.Event:
    """Register a fresh cancel token for one wake chain's whole capture window.

    The token must exist BEFORE capture_utterance runs: a cancel that fires
    while the chain is still transcribing must survive until the recording
    thread actually starts."""
    global _current_capture_token
    token = threading.Event()
    with _capture_token_lock:
        _current_capture_token = token
    return token


def end_capture_scope(token: threading.Event) -> None:
    """Unregister the wake chain's token so later cancels stay no-ops."""
    global _current_capture_token
    with _capture_token_lock:
        if _current_capture_token is token:
            _current_capture_token = None


def cancel_utterance_capture() -> None:
    """Abort the registered capture window (the voice button preempts wake)."""
    with _capture_token_lock:
        token = _current_capture_token
    if token is not None:
        token.set()


def capture_utterance(
    cancel_event: threading.Event | None = None,
    max_seconds: float = 8.0,
    min_speech_seconds: float = 0.4,
    end_silence_seconds: float = 1.2,
    speech_level: float = 0.004,
) -> bytes | None:
    """Record one utterance with a silence endpoint; returns WAV bytes or None.

    Aborts with None as soon as cancel_event is set (pass the token from
    begin_capture_scope), so a voice-button press can preempt a waiting
    wake-command recording — including a cancel that arrived before this
    call started."""
    if cancel_event is not None and cancel_event.is_set():
        return None
    np, sd = _import_audio_dependencies()
    collected: list[Any] = []
    state = "waiting"
    speech_seconds = 0.0
    silence_seconds = 0.0
    total_seconds = 0.0
    block_seconds = 0.1
    frames = int(capture_rate() * block_seconds)
    stream = None
    try:
        stream = sd.InputStream(
            samplerate=capture_rate(),
            channels=1,
            dtype="float32",
            blocksize=frames,
        )
        stream.start()
    except Exception as exc:
        if stream is not None:
            try:
                stream.close()
            except Exception:
                pass
        raise VoiceError("无法打开默认麦克风，请检查 Windows 麦克风权限") from exc
    try:
        while total_seconds < max_seconds:
            if cancel_event is not None and cancel_event.is_set():
                return None
            data, _overflow = stream.read(frames)
            chunk = data.reshape(-1)
            collected.append(chunk.copy())
            total_seconds += block_seconds
            peak = float(np.max(np.abs(chunk)))
            if state == "waiting":
                if peak >= speech_level:
                    state = "speech"
            elif peak >= speech_level:
                silence_seconds = 0.0
                speech_seconds += block_seconds
            else:
                silence_seconds += block_seconds
                if speech_seconds >= min_speech_seconds and silence_seconds >= end_silence_seconds:
                    break
    finally:
        try:
            stream.stop()
            stream.close()
        except Exception:
            pass
    if state != "speech" or speech_seconds < min_speech_seconds:
        return None
    audio = np.concatenate(collected, axis=0).reshape(-1)
    pcm = np.clip(audio, -1.0, 1.0)
    pcm = (pcm * 32767.0).astype(np.int16).tobytes()
    output = io.BytesIO()
    with wave.open(output, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(capture_rate())
        wav_file.writeframes(pcm)
    return output.getvalue()


def encode_wav(audio: Any) -> bytes:
    """Encode float32 mono samples as 16kHz 16-bit WAV bytes."""
    import numpy as np
    pcm = np.clip(audio, -1.0, 1.0)
    pcm = (pcm * 32767.0).astype(np.int16).tobytes()
    output = io.BytesIO()
    with wave.open(output, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(capture_rate())
        wav_file.writeframes(pcm)
    return output.getvalue()


def capture_rate() -> int:
    return WakeWordListener.sample_rate
