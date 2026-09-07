from __future__ import annotations

import io
import logging
import os
import threading
import time
import wave
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)
if not logger.handlers:  # per-recording level lines must reach core.stderr.log
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s %(name)s %(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)

# zcode (2026-09-07, KI-001): the Realtek array on this machine wedges by
# delivering exact digital zeros (see docs/HANDOFF.md known traps). A live
# microphone always has a nonzero noise floor, so "peak below a couple of
# LSBs across the whole recording" is a reliable wedge signature — it also
# never fires for a user who simply stayed quiet.
_WEDGE_LSB_THRESHOLD = 4.0


def _is_driver_wedge(peak_amplitude: float) -> bool:
    return abs(peak_amplitude) * 32767.0 < _WEDGE_LSB_THRESHOLD


class VoiceError(RuntimeError):
    """A local microphone or speech-to-text failure safe to show in the UI."""


class VoiceRecorder:
    sample_rate = 16_000

    def __init__(self) -> None:
        self._stream: Any = None
        self._samples: list[Any] = []
        self._numpy: Any = None
        self._lock = threading.Lock()

    @property
    def recording(self) -> bool:
        return self._stream is not None

    def start(self) -> None:
        if self.recording:
            return
        try:
            import numpy as np
            import sounddevice as sd
        except ImportError as exc:
            raise VoiceError("语音依赖尚未安装，请先安装 agent-core[voice]") from exc

        self._numpy = np
        self._samples = []
        try:
            stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32",
                callback=self._callback,
            )
            stream.start()
        except Exception as exc:  # sounddevice exposes platform-specific exceptions
            self._stream = None
            raise VoiceError("无法打开默认麦克风，请检查 Windows 麦克风权限") from exc
        self._stream = stream

    def stop(self) -> bytes:
        stream = self._stream
        self._stream = None
        if stream is None:
            raise VoiceError("当前没有正在进行的录音")
        try:
            stream.stop()
            stream.close()
        except Exception as exc:
            raise VoiceError("停止录音失败") from exc

        with self._lock:
            samples = list(self._samples)
            self._samples.clear()
        if not samples or self._numpy is None:
            raise VoiceError("没有录到有效声音")

        audio = self._numpy.concatenate(samples, axis=0).reshape(-1)
        peak = float(self._numpy.max(self._numpy.abs(audio))) if audio.size else 0.0
        duration = len(audio) / float(self.sample_rate)
        logger.info("mic recording level: peak=%.6f (%.1fs)", peak, duration)
        if _is_driver_wedge(peak):
            reopened = self._attempt_device_reset()
            logger.warning("mic wedge suspected (peak=%.6f); device reopen=%s", peak, reopened)
            hint = "" if reopened else "（本次自动重置未成功）"
            raise VoiceError(
                "麦克风全程只录到数字静音，像是驱动假死了" + hint +
                "。我已经重置过麦克风，请再按住语音说一次；如果还是不行，"
                "按一下 Fn 静音键或运行一次 Windows 麦克风测试就能唤醒它。"
            )
        pcm = self._numpy.clip(audio, -1.0, 1.0)
        pcm = (pcm * 32767.0).astype(self._numpy.int16).tobytes()
        output = io.BytesIO()
        with wave.open(output, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(pcm)
        return output.getvalue()

    def _attempt_device_reset(self, sd_module: Any = None) -> bool:
        """One automatic reopen of the default input device; best-effort."""
        try:
            if sd_module is None:
                import sounddevice as sd_module  # noqa: PLC0415
            probe = sd_module.InputStream(
                samplerate=self.sample_rate, channels=1, dtype="float32"
            )
            probe.start()
            probe.stop()
            probe.close()
            return True
        except Exception:  # noqa: BLE001 - reset is best-effort by design
            return False

    def cancel(self) -> None:
        stream = self._stream
        self._stream = None
        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception:
                pass
        with self._lock:
            self._samples.clear()

    def _callback(self, indata: Any, _frames: int, _time: Any, _status: Any) -> None:
        with self._lock:
            self._samples.append(indata.copy())


_stt_model: Any = None
_stt_lock = threading.Lock()


def transcribe_wav(audio_bytes: bytes) -> str:
    global _stt_model
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise VoiceError("语音识别依赖尚未安装，请先安装 agent-core[voice]") from exc

    if _stt_model is None:
        with _stt_lock:
            if _stt_model is None:
                model_name = os.getenv("STT_MODEL", "small")
                device = os.getenv("STT_DEVICE", "cpu")
                compute_type = os.getenv("STT_COMPUTE_TYPE", "int8")
                try:
                    _stt_model = WhisperModel(
                        model_name,
                        device=device,
                        compute_type=compute_type,
                    )
                except Exception as exc:
                    raise VoiceError("语音模型加载失败，请检查模型文件和设备配置") from exc

    try:
        try:
            segments, _info = _stt_model.transcribe(
                io.BytesIO(audio_bytes),
                language="zh",
                vad_filter=True,
            )
        except ModuleNotFoundError as exc:
            if exc.name != "onnxruntime":
                raise
            segments, _info = _stt_model.transcribe(
                io.BytesIO(audio_bytes),
                language="zh",
                vad_filter=False,
            )
        text = "".join(segment.text for segment in segments).strip()
    except Exception as exc:
        raise VoiceError("语音转文字失败") from exc
    if not text:
        raise VoiceError("没有识别到清晰语音")
    return text
