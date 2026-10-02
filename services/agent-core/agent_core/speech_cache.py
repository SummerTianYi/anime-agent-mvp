"""Codex: pin accepted farewell WAVs outside the sidecar's expiring spool.

No model/voice changes or historical data access. Files are refreshed atomically
each session; old disk content is never implicitly trusted as the current voice.
"""
import hashlib
import os
from pathlib import Path
import shutil
import uuid
import wave


def wav_info(path: Path) -> dict:
    try:
        stream = wave.open(str(path), 'rb')
    except (wave.Error, EOFError) as exc:
        raise ValueError('Invalid farewell WAV') from exc
    with stream as wav:
        frames, rate = wav.getnframes(), wav.getframerate()
        width, channels = wav.getsampwidth(), wav.getnchannels()
        if frames <= 0 or rate <= 0 or frames > rate * 30 or channels not in (1, 2) or width not in (1, 2):
            raise ValueError('Unsupported or empty farewell WAV')
        if len(wav.readframes(frames)) != frames * channels * width:
            raise ValueError('Truncated farewell WAV')
    return {'audioPath':str(path), 'durationMs':round(frames * 1000 / rate), 'sampleRate':rate}


def pin_farewell(directory: Path, line: str, audio: dict) -> dict:
    source = Path(audio['audioPath'])
    wav_info(source)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / (hashlib.sha256(line.encode('utf-8')).hexdigest()[:24] + '.wav')
    staging = directory / (target.stem + '.' + uuid.uuid4().hex + '.tmp')
    try:
        shutil.copyfile(source, staging)
        wav_info(staging)
        os.replace(staging, target)
    finally:
        staging.unlink(missing_ok=True) # Only this call's generated temporary file.
    return wav_info(target)
