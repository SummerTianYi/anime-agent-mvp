"""Single loaded Tianyi sidecar, fixed text, isolated Core/WS + visible real Godot role.
Inputs: authorized installed voice and a private cached role project as in the parent report.
"""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys

import psutil
import uvicorn
import websockets
from live_metrics import LiveClient, TakeObserver, gpu, health, now_ms, sample_resources, side_status

ROOT = Path(__file__).resolve().parents[3]
PREVIOUS = Path(__file__).resolve().parents[1] / "speech-lip-continuity"
SHORT = "我在，请讲。"
LONG = ("刚才雨停了，窗边有一点阳光。小小的水珠还挂在叶子上。\n"
        "书可以慢慢读。我们把最喜欢的那句话夹在蓝色书签里，留给明天。\n等会儿，再一起听听窗外的风吧。")
# Counterbalance both modes, with fresh synthesis on every turn.
MATRIX = [(1,"short"), (2,"short"), (1,"long"), (2,"long"),
          (2,"short"), (1,"short"), (2,"long"), (1,"long")]


def clean_core(scratch):
    for key in list(os.environ):
        if key.startswith(("ANIME_AGENT_","DEEPSEEK_","GLM_","LLM_","STEPFUN_","TTS_","AGENT_CORE_")):
            del os.environ[key]
    os.environ.update(ANIME_AGENT_DATA_DIR=str(scratch/"data"), ANIME_AGENT_CONFIG_PATH=str(scratch/"absent.env"),
                     LLM_PROVIDER="mock", ANIME_AGENT_TTS="1", ANIME_AGENT_TTS_NARRATE="0",
                     ANIME_AGENT_WAKE_WORD="0", ANIME_AGENT_FAREWELL_PRECACHE="0", ANIME_AGENT_MCP_SERVERS="",
                     ANIME_AGENT_IDLE_THRESHOLD="0", ANIME_AGENT_TOOLS="0", TTS_SERVICE_URL="http://127.0.0.1:8770")
    sys.path.insert(0,str(ROOT/"services/agent-core"))
    from agent_core import main as core
    assert core.memory.path.parent.resolve()==(scratch/"data").resolve()
    assert core.provider.name=="mock" and core.speech_manager.lookahead==1
    core.proactive_policy.mark_spoken()  # no incidental greeting in the measurement window
    return core


def public_events(core):
    kinds = ("speech.timing","speech.receipt","speech.completed","speech.interrupted","speech.unavailable")
    events = []
    for kind, raw in core.memory.connection.execute("SELECT event_type,payload FROM events ORDER BY id"):
        if kind in kinds:
            d = json.loads(raw)
            keep = ("requestId","request_id","utteranceId","partIndex","stage","atMs","preparationId","playbackId",
                    "selectedTake","selectedAtMs","takes","priority","queuedPriority","queueWaitMs","failed",
                    "startedAtMs","endedAtMs","interrupted","reason")
            events.append(dict(kind=kind, **{k:d[k] for k in keep if k in d}))
    return events


def summarize(report, split):
    requests = [e for e in report["coreEvents"] if e.get("stage")=="synth-request"]
    calls = report["calls"]
    assert len(requests)==len(calls)
    for call, event in zip(calls,requests,strict=True):
        call.update(requestId=event["requestId"], partIndex=event["partIndex"], preparationId=event["preparationId"])
        case = next(c for c in report["cases"] if c["id"]==call["requestId"])
        assert call["text"]==split(case["text"])[call["partIndex"]]
    for case in report["cases"]:
        request = case["id"]
        rows = [r for r in calls if r["requestId"]==request]
        plays = [w for w in report["wireSpeak"] if w["requestId"]==request]
        ids = [p["playbackId"] for p in plays]
        receipts = [r for r in report["wireReceipts"] if r["playbackId"] in ids]
        stages = [e for e in report["coreEvents"] if e.get("requestId")==request]
        ready = {e["partIndex"]:e["atMs"] for e in stages if e.get("stage")=="ready"}
        assert len(receipts)==len(ids)==len(set(ids))
        if case["label"]=="cancel":
            assert len(plays)==1 and receipts[0]["interrupted"] and case["completed"] is False
            assert not any(e["kind"]=="speech.completed" and e.get("request_id")==request for e in report["coreEvents"])
            case["completedHttpWithoutPlayback"] = len(rows)-1
            continue
        assert case["completed"] and [p["text"] for p in plays]==split(case["text"])
        assert [r["playbackId"] for r in receipts]==ids and len(plays)==len(rows)==len(ready)
        assert all(not r["interrupted"] and r["type"]=="speech.finished" and r["firstSoundMs"]>0 for r in receipts)
        confirmed = [e["playbackId"] for e in report["coreEvents"] if e["kind"]=="speech.receipt" and e["playbackId"] in ids]
        assert confirmed==ids and all(r["checks"]>=1 for r in rows)
        assert any(e["kind"]=="speech.completed" and e.get("request_id")==request for e in report["coreEvents"])
        waits = [max(0,ready[i]-receipts[i-1]["relayAtMs"]) for i in range(1,len(plays))]
        case.update(firstSoundMs=receipts[0]["firstSoundMs"]-case["startMs"], waitForFileMs=waits,
                    waitsOver80Ms=sum(ms>80 for ms in waits), longestWaitMs=max(waits,default=0),
                    wavEdgeSilenceMs=[round(rows[i-1]["pcm"]["trailingMs"]+rows[i]["pcm"]["leadingMs"],1)
                                      for i in range(1,len(rows))],
                    audibleIntervalMs=[receipts[i]["firstSoundMs"]-receipts[i-1]["lastSoundMs"] for i in range(1,len(plays))],
                    queueMs=[e["queueWaitMs"] for e in stages if e.get("stage")=="synth-request"],
                    retries=sum(r["retries"] for r in rows))
    samples = report["resources"]
    for case in report["cases"]:
        used = [s for s in samples if case["startMs"]<=s["atMs"]<=case["endMs"]]
        if used:
            case["peaksMiB"] = {k:max(s[k] for s in used) for k in ("usedGpuMiB","coreRssMiB","roleRssMiB","ttsRssMiB")}
            case["minFreeRamMiB"] = min(s["freeMiB"] for s in used)


async def run(a):
    assert (a.project/"runtime.gd").read_bytes().replace(b"\r\n",b"\n")==(
        ROOT/"apps/avatar-runtime/runtime.gd").read_bytes().replace(b"\r\n",b"\n")
    assert "Tianyi private lipsync lab" in (a.project/"project.godot").read_text(encoding="utf8")
    assert not a.output.exists()
    a.scratch.mkdir(parents=True,exist_ok=False)
    core = clean_core(a.scratch)
    from agent_core.speech import split_reply_into_parts
    client = LiveClient(core.speech_client,a.spool,[SHORT,*split_reply_into_parts(LONG)])
    core.speech_manager.client = client
    assert client.initial["phase"]=="ready" and client.initial["device"]=="cuda" and core.TTS_ENABLED
    assert client.initial["selfCheck"]["enabled"] and client.initial["selfCheck"]["threshold"]==.9
    assert psutil.virtual_memory().available>1100*1048576 and not health(8765)["tts"]["speechPending"]
    adapter = gpu()
    assert adapter["totalGpuMiB"]-adapter["usedGpuMiB"]>1000
    data = dict(initialSidecar=client.initial, calls=client.calls, wireSpeak=[], wireReceipts=[], cases=[],
                resources=[], initialGpu=adapter, llmCalls=0,
                runtimeSHA256=hashlib.sha256((a.project/"runtime.gd").read_bytes()).hexdigest())
    async def unexpected_model(*args,**kwargs):
        data["llmCalls"] += 1
        raise AssertionError("fixed replies must never call any LLM")
    core.provider.complete = core.provider.complete_with_tools = unexpected_model
    observer = TakeObserver(a.numeric_log, client.allowed)
    stopping = asyncio.Event()
    async def tail():
        while not stopping.is_set():
            observer.poll()
            await asyncio.sleep(.015)
    tasks = [asyncio.create_task(tail())]
    loop = asyncio.get_running_loop()
    connected = loop.create_future()
    def accept(r,w):
        if not connected.done():
            connected.set_result((r,w))
        else:
            w.close()
    tcp = await asyncio.start_server(accept,"127.0.0.1",0)
    port = tcp.sockets[0].getsockname()[1]
    sock = socket.socket()
    sock.bind(("127.0.0.1",0))
    ws_port = sock.getsockname()[1]
    assert ws_port not in (8765,8770)
    server = uvicorn.Server(uvicorn.Config(core.app,log_level="error",lifespan="off"))
    serving = asyncio.create_task(server.serve(sockets=[sock]))
    child = None
    ws = writer = None
    try:
        async with asyncio.timeout(12):
            while not server.started:
                await asyncio.sleep(.02)
        isolated = await asyncio.to_thread(health,ws_port)
        assert isolated["status"]=="ok" and isolated["tts"]["available"]
        assert Path(isolated["memory"]["path"]).resolve()==core.memory.path.resolve()
        env = dict(os.environ,LIP_BENCH_PORT=str(port),ANIME_AGENT_SPEECH_GAIN_DB="5",AGENT_CORE_WS_URL="ws://127.0.0.1:1")
        exe = a.godot.with_name(a.godot.name.replace("_console.exe",".exe"))
        cmd = [str(exe),"--path",str(a.project),"--rendering-method","gl_compatibility","--audio-driver","WASAPI",
               "--max-fps","30","--log-file",str(a.scratch/"role.log"),"--script",str(PREVIOUS/"role_probe.gd")]
        with (a.scratch/"launcher.log").open("wb") as log:
            child = subprocess.Popen(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        tasks.append(asyncio.create_task(sample_resources(data["resources"],psutil.Process(client.initial["pid"]),
                                                          psutil.Process(child.pid),client,stopping)))
        reader,writer = await asyncio.wait_for(connected,18)
        assert json.loads(await asyncio.wait_for(reader.readline(),5))["type"]=="ready"
        ws = await websockets.connect(f"ws://127.0.0.1:{ws_port}/ws",proxy=None)
        await ws.send(json.dumps({"type":"client.hello","role":"avatar"}))
        while json.loads(await ws.recv())["type"]!="client.ready":
            pass
        async def avatar_output():
            async for raw in ws:
                d = json.loads(raw)
                if d["type"]=="avatar.speak":
                    data["wireSpeak"].append({k:d[k] for k in ("requestId","utteranceId","playbackId","partIndex","text")})
                    writer.write((json.dumps(dict(d,type="speak"))+"\n").encode())
                    await writer.drain()
                elif d["type"]=="avatar.speech.stop":
                    writer.write((json.dumps(dict(d,type="stop"))+"\n").encode())
                    await writer.drain()
        async def avatar_receipts():
            while line := await reader.readline():
                d = json.loads(line)
                assert d["type"] in ("speech.finished","speech.failed")
                data["wireReceipts"].append(dict(d,relayAtMs=now_ms()))
                await ws.send(json.dumps(d))
        tasks.extend(asyncio.create_task(f()) for f in (avatar_output,avatar_receipts))
        async def trial(n,label,text):
            assert not client.stop.is_set()
            case = dict(id=f"priority-{len(data['cases'])+1}", window=n, label=label, text=text,startMs=now_ms())
            data["cases"].append(case)
            core.speech_manager.lookahead = n
            case["completed"] = await asyncio.wait_for(core._speak_reply(text,case["id"]),120)
            case["endMs"] = now_ms()
            if label!="cancel" and not case["completed"]:
                raise RuntimeError("no completion; examine receipts")
        for n,label in MATRIX:
            await trial(n,label,SHORT if label=="short" else LONG)
            print("Completed",label,n,flush=True)
        old = asyncio.create_task(trial(2,"cancel",LONG))
        async with asyncio.timeout(35):
            while not any(d["requestId"]=="priority-9" for d in data["wireSpeak"]):
                if old.done():
                    await old
                    raise RuntimeError("cancel fixture finished before dispatch")
                await asyncio.sleep(.01)
        await asyncio.sleep(.4)
        assert await core.speech_manager.interrupt("voice")
        await old
        await trial(2,"recovery",SHORT)
        await asyncio.sleep(.1)
        data["coreEvents"] = public_events(core)
        summarize(data, split_reply_into_parts)
        data["status"] = "complete"
    except BaseException as exc:
        data["status"] = "incomplete"
        data["failure"] = type(exc).__name__
        raise
    finally:
        client.stop.set()
        stopping.set()
        # An HTTP worker may still be finishing. Do not kill or restart the sidecar.
        async with asyncio.timeout(95):
            while core.speech_manager._synthesis_worker is not None:
                await asyncio.sleep(.05)
        if writer is not None:
            writer.write(b'{"type":"quit"}\n')
            try:
                await writer.drain()
            except ConnectionError:
                pass
        if ws is not None:
            await ws.close()
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks,return_exceptions=True)
        if writer is not None:
            writer.close()
        tcp.close()
        await tcp.wait_closed()
        if child is not None:
            try:
                await asyncio.to_thread(child.wait,3)
            except subprocess.TimeoutExpired:
                child.terminate()
                await asyncio.to_thread(child.wait,5)
        server.should_exit = True
        await asyncio.wait_for(serving,8)
        data["coreEvents"] = public_events(core)
        observer.join(client.calls)
        data["finalSidecar"] = side_status()
        core.memory.close()
        a.output.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf8")


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    for k in ("scratch","project","godot","spool","numeric-log","output"):
        parser.add_argument("--"+k,type=Path,required=True)
    asyncio.run(run(parser.parse_args()))
