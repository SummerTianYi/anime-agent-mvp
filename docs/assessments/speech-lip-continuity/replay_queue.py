"""Wall-clock A/B with a visible role and archived voice PCM. Only preparation times are injected."""
import argparse
import asyncio
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import wave

import psutil

SHORT = "我在，请讲。"
LONG = "你好呀，我是天依。现在的声音听得清楚吗？\n今天也辛苦啦。我们可以慢慢聊，一起把想做的事情安排好。\n我在，请讲。"
# Split in the recorded inter-sentence silence. Concatenating slices restores all PCM bytes.
SOURCES = [("short", 1.82, ["你好呀，我是天依。", "现在的声音听得清楚吗？"]),
           ("long", 1.36, ["今天也辛苦啦。", "我们可以慢慢聊，一起把想做的事情安排好。"]),
           ("ack", None, [SHORT])]
DELAYS = [.65, .70, .55, 3.0, .90]  # seconds; deliberately late fourth segment

def fixtures(source, scratch):
    clips = {}
    for name, split, texts in SOURCES:
        with wave.open(str(source / (name + ".wav"))) as f:
            params = f.getparams()
            raw = f.readframes(params.nframes)
        cut = int(split * params.framerate) * params.nchannels * params.sampwidth if split else len(raw)
        slices = [raw[:cut], raw[cut:]] if split else [raw]
        assert b"".join(slices) == raw
        for i, (text, pcm) in enumerate(zip(texts, slices)):
            path = scratch / f"{name}-{i}.wav"
            with wave.open(str(path), "wb") as w:
                w.setparams(params)
                w.writeframes(pcm)
            duration = 1000 * len(pcm) / (params.framerate * params.nchannels * params.sampwidth)
            clips[text] = dict(audioPath=str(path), durationMs=round(duration), sampleRate=params.framerate)
    return clips

def load_speech(path):
    spec = importlib.util.spec_from_file_location("replay_speech", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod

def now():
    return time.time_ns() // 1_000_000

async def trial(mod, clips, text, window, reader, writer):
    trace, receipts, sent = [], [], []
    active = peak = 0
    lock = threading.Lock()
    parts = mod.split_reply_into_parts(text)
    assert "".join(parts) == text.replace("\n", "")
    delays = dict(zip(parts, DELAYS if text == LONG else [.90]))
    class Replay:
        def synthesize(self, part, speed):
            nonlocal active, peak
            assert speed == 1.0
            with lock:
                active += 1
                peak = max(peak, active)
            index = parts.index(part)
            trace.append(dict(part=index, stage="prepare", at=now()))
            time.sleep(delays[part])
            with lock:
                active -= 1
            trace.append(dict(part=index, stage="ready", at=now()))
            return clips[part].copy()
    async def play(payload):
        sent.append(payload["partIndex"])
        trace.append(dict(part=sent[-1], stage="dispatch", at=now()))
        writer.write((json.dumps(dict(payload, type="speak")) + "\n").encode())
        await writer.drain()
    async def stop(*args):
        raise AssertionError("Unexpected playback failure")
    mgr = mod.SpeechManager(Replay(), play, stop, **({"lookahead": window} if window else {}))
    async def listen():
        for index in range(len(parts)):
            item = json.loads(await asyncio.wait_for(reader.readline(), 15))
            assert item["type"] == "speech.finished" and item["partIndex"] == index and not item["interrupted"]
            assert item["firstSoundMs"] > 0 and item["lastSoundMs"] >= item["firstSoundMs"]
            assert await mgr.notify_finished(item["utteranceId"], item["playbackId"])
            receipts.append(dict(part=index, at=now(), first=item["firstSoundMs"], last=item["lastSoundMs"]))
    start = now()
    result, _ = await asyncio.gather(mgr.speak(text, "synthetic"), listen())
    assert result.completed and sent == list(range(len(parts))) and peak == 1
    ready = {e["part"]: e["at"] for e in trace if e["stage"] == "ready"}
    supply = [max(0, ready[i]-receipts[i-1]["at"]) for i in range(1,len(parts))]
    boundaries = [receipts[i]["first"]-receipts[i-1]["last"] for i in range(1,len(parts))]
    dispatch = {e["part"]: e["at"] for e in trace if e["stage"] == "dispatch"}
    # Count selected files waiting behind the part currently playing, omit the first part.
    depth = max(sum(ready[j] <= e["at"] < dispatch[j] for j in range(1,len(parts))) for e in trace)
    return dict(scenario="short" if text==SHORT else "three-paragraph", injectionMs=[round(delays[p]*1000) for p in parts],
                firstSoundMs=receipts[0]["first"]-start, waitingForFileMs=supply, audibleIntervalsMs=boundaries,
                over80ms=sum(g>80 for g in supply), longestMs=max(supply,default=0), peakReadyFiles=depth,
                peakModelWorkers=peak, selectedAudioMs=[clips[p]["durationMs"] for p in parts],
                events=[dict(e, at=e["at"]-start) for e in trace],
                receipts=[{k: v if k=="part" else v-start for k,v in e.items()} for e in receipts])

async def run(a):
    if "Tianyi private lipsync lab" not in (a.project/"project.godot").read_text(encoding="utf8"):
        raise SystemExit("Use a private copy with its own project/user ID and imported role")
    if psutil.virtual_memory().available < 1100 * 1024**2:
        raise SystemExit("Insufficient free memory for the isolated cached role")
    mod = load_speech(a.speech)
    fingerprint = hashlib.sha256(a.speech.read_bytes()).hexdigest()
    a.private.mkdir(parents=True,exist_ok=True)
    clips = fixtures(a.audio,a.private)
    connected = asyncio.get_running_loop().create_future()
    def accept(r,w):
        if not connected.done():
            connected.set_result((r,w))
        else:
            w.close()
    server = await asyncio.start_server(accept, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    env = dict(os.environ,LIP_BENCH_PORT=str(port),ANIME_AGENT_SPEECH_GAIN_DB="5",AGENT_CORE_WS_URL="ws://127.0.0.1:1")
    binary = a.godot.with_name(a.godot.name.replace("_console.exe",".exe"))
    cmd = [str(binary),"--path",str(a.project),"--rendering-method","gl_compatibility","--max-fps","30",
           "--audio-driver","WASAPI","--log-file",str(a.private/"engine.log"),"--script",str(Path(__file__).with_name("role_probe.gd"))]
    with (a.private/"launch.log").open("wb") as log:
        proc = subprocess.Popen(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        child = psutil.Process(proc.pid)
        resources = dict(minimumFreeMiB=999999,peakRoleMiB=0)
        async def guard():
            while proc.poll() is None:
                free = psutil.virtual_memory().available // 1024**2
                resources["minimumFreeMiB"] = min(resources["minimumFreeMiB"],free)
                try:
                    resources["peakRoleMiB"] = max(resources["peakRoleMiB"],child.memory_info().rss // 1024**2)
                except psutil.NoSuchProcess:
                    break
                if free < 450:
                    proc.terminate()
                    raise RuntimeError("Isolated role stopped by RAM guard")
                await asyncio.sleep(.2)
        watch = asyncio.create_task(guard())
        try:
            r,w = await asyncio.wait_for(connected,20)
            assert json.loads(await asyncio.wait_for(r.readline(),5))["type"]=="ready"
            results=[]
            for rep in range(2):
                for text in (SHORT,LONG):
                    results.append(await trial(mod,clips,text,a.window,r,w))
            w.write(b'{"type":"quit"}\n')
            await w.drain()
            await asyncio.to_thread(proc.wait,5)
            w.close()
            await w.wait_closed()
            assert proc.returncode == 0
            report=dict(window=a.window or "baseline", runs=results, resources=resources,
                        sourceSha256=fingerprint)
            a.output.write_text(json.dumps(report,indent=2)+"\n",encoding="utf8")
        finally:
            if proc.poll() is None:
                proc.terminate()
            await watch
            server.close()
            await server.wait_closed()

if __name__=="__main__":
    p=argparse.ArgumentParser()
    for k in ("godot","project","speech","audio","private","output"):
        p.add_argument("--"+k,type=Path,required=True)
    p.add_argument("--window",type=int,choices=[0,1,2],required=True)
    asyncio.run(run(p.parse_args()))
