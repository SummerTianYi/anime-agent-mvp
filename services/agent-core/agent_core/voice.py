from __future__ import annotations

import io
import os
import threading
import wave
from typing import Any


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
        pcm = self._numpy.clip(audio, -1.0, 1.0)
        pcm = (pcm * 32767.0).astype(self._numpy.int16).tobytes()
        output = io.BytesIO()
        with wave.open(output, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(pcm)
        return output.getvalue()

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
