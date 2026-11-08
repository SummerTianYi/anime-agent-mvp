"""Measurement of the existing local sidecar. Keep only synthetic labels and numbers."""
import asyncio
import json
from pathlib import Path
import re
import subprocess
import threading
import time
import urllib.request
import wave

import numpy as np
import psutil


def now_ms():
    return time.time_ns() // 1_000_000


def health(port):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(f"http://127.0.0.1:{port}/health", timeout=3) as r:
        return json.load(r)


def side_status():
    h = health(8770)
    assert h["service"] == "tianyi-tts"
    return {k:h[k] for k in ("pid","phase","device","ok","selfCheck","synthCount")}


def source_pauses(path):
    """Original PCM, before output gain; contiguous quiet interior runs of at least 80 ms."""
    with wave.open(str(path)) as w:
        rate, channels = w.getframerate(), w.getnchannels()
        assert w.getsampwidth() == 2 and w.getcomptype()=="NONE"
        a = np.frombuffer(w.readframes(w.getnframes()),dtype="<i2").reshape(-1,channels)
    loud = np.max(np.abs(a.astype(np.int32)),axis=1) > .003*32768
    ix = np.flatnonzero(loud)
    assert ix.size
    edges = np.diff(ix)-1
    return dict(samples=len(a), rate=rate, leadingMs=round(ix[0]*1000/rate,1),
                trailingMs=round((len(a)-ix[-1]-1)*1000/rate,1),
                interiorQuietMs=[round(float(n)*1000/rate,1) for n in edges[edges >= .080*rate]])


class LiveClient:
    def __init__(self, real, spool, allowed):
        self.real, self.spool, self.allowed = real, spool.resolve(), set(allowed)
        self.initial = self.expected = side_status()
        self.stop = threading.Event()
        self.calls = []
        self.live_lock = threading.Lock()
        self.blocked = None

    def synthesize(self, text, speed):
        # The production Core has its own manager. Yield before every synthesis
        # if it wants to speak. Detect foreign jobs from the on-service counters.
        if self.stop.is_set() or text not in self.allowed or speed != 1.0:
            raise RuntimeError("probe stopped or unexpected voice input")
        if not self.live_lock.acquire(blocking=False):
            raise AssertionError("overlapping real synthesis from this Core")
        try:
            prod = health(8765)
            before = side_status()
            if not (prod["status"]=="ok" and prod["tts"]["available"] and not prod["tts"]["speechPending"]
                    and before["pid"]==self.initial["pid"] and before["phase"]=="ready"
                    and before["synthCount"]==self.expected["synthCount"]
                    and before["selfCheck"]==self.expected["selfCheck"]):
                self.stop.set()
                raise RuntimeError("official voice activity or service change; pausing the probe")
            names = {p.name for p in self.spool.glob("utt_*.wav")}
            call = dict(sequence=len(self.calls)+1, text=text, before=before["synthCount"],
                        httpStartMs=now_ms())
            self.calls.append(call)
            audio = self.real.synthesize(text, speed)
            call["httpEndMs"] = now_ms()
            after = side_status()
            checks = after["selfCheck"]
            retries = checks["retries"] - before["selfCheck"]["retries"]
            assert after["pid"]==before["pid"] and after["synthCount"]==before["synthCount"]+1
            assert checks["enabled"] and checks["threshold"]==.9 and checks["takes"]==before["selfCheck"]["takes"]+1
            assert retries in (0,1)
            self.expected = after
            path = Path(audio["audioPath"]).resolve()
            assert path.parent==self.spool and path.name not in names and re.fullmatch(r"utt_[a-f0-9]{32}\.wav",path.name)
            new = sorted((p for p in self.spool.glob("utt_*.wav") if p.name not in names),
                         key=lambda p:p.stat().st_mtime_ns)
            ordered = len(new)==1+retries and len({p.stat().st_mtime_ns for p in new})==len(new)
            call.update(after=after["synthCount"], checks=1+retries, retries=retries, durationMs=audio["durationMs"],
                        selectedTakeByFileOrder=(new.index(path)+1 if ordered else None), pcm=source_pauses(path))
            if "takeTiming" in audio:
                call["sidecarTakeTiming"] = audio["takeTiming"]
            return audio
        except BaseException as exc:
            self.stop.set()
            self.blocked = type(exc).__name__ + ": " + str(exc)[:180]
            raise
        finally:
            self.live_lock.release()


class TakeObserver:
    """Tail only new stdout bytes from this window; drop every non-metric immediately."""
    def __init__(self, stream_path, texts):
        self.f = stream_path.open("rb")
        self.f.seek(0, 2)
        self.rest = b""
        self.markers = {("实际输入的目标文本: " + t).encode(enc):t
                        for t in texts for enc in ("gb18030","utf8")}
        self.takes = []
        self.jobs = {}

    def poll(self):
        chunk = self.f.read()
        if not chunk:
            return
        lines = (self.rest+chunk).split(b"\n")
        self.rest = lines.pop()
        at = now_ms()
        for raw in lines:
            line = raw.strip()
            if line in self.markers:
                self.takes.append(dict(text=self.markers[line], startObservedMs=at))
            elif self.takes and re.fullmatch(rb"(?:\d+\.\d+\t){3}\d+\.\d+",line):
                self.takes[-1].update(stageMs=[round(float(n)*1000) for n in line.split()], metricsObservedMs=at)
            elif m := re.fullmatch(rb"TTS_SYNTH_OK count=(\d+)",line):
                self.jobs[int(m.group(1))] = dict(takes=self.takes, successObservedMs=at)
                self.takes = []

    def join(self, calls):
        self.poll()
        for call in calls:
            j = self.jobs.get(call.get("after"))
            if not j:
                continue
            takes = j["takes"]
            if len(takes)!=call["checks"] or any(t["text"]!=call["text"] or "metricsObservedMs" not in t for t in takes):
                continue
            call["numericLog"] = j
            for i,t in enumerate(takes):
                end = takes[i+1]["startObservedMs"] if i+1<len(takes) else j["successObservedMs"]
                t["postSynthIncludingCheckMs"] = end-t["metricsObservedMs"]
        self.f.close()


def gpu():
    out = subprocess.check_output(["nvidia-smi","--query-gpu=memory.total,memory.used,utilization.gpu",
                                   "--format=csv,noheader,nounits"], timeout=4,
                                  creationflags=subprocess.CREATE_NO_WINDOW, text=True)
    total, used, load = map(int,out.splitlines()[0].split(","))
    return dict(totalGpuMiB=total, usedGpuMiB=used, gpuPercent=load)


async def sample_resources(resources, tts, godot, client, stop):
    this = psutil.Process()
    while not stop.is_set():
        h = await asyncio.to_thread(gpu)
        try:
            h.update(atMs=now_ms(), freeMiB=psutil.virtual_memory().available//1048576,
                     ttsRssMiB=tts.memory_info().rss//1048576, roleRssMiB=godot.memory_info().rss//1048576,
                     coreRssMiB=this.memory_info().rss//1048576)
        except psutil.NoSuchProcess:
            client.stop.set()
            return
        resources.append(h)
        if h["freeMiB"]<450 or h["totalGpuMiB"]-h["usedGpuMiB"]<350:
            client.stop.set()
        await asyncio.sleep(.3)
