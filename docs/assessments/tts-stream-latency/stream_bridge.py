"""Local WS integration bench. Replay generated PCM, or consume a live private inference queue."""
import argparse
import base64
import json
import os
from pathlib import Path
import subprocess
import threading
import time
import wave
from websockets.sync.server import serve

def pcm_message(i,data):
    return {"type":"chunk","seq":i,"pcm":base64.b64encode(data).decode("ascii")}

def run(a):
    done=threading.Event()
    failures=[]
    rows=[]
    def handle(ws):
        def send(id,message):
            ws.send(json.dumps(dict(message,id=id)))
        def event(id,wanted):
            while True:
                message=json.loads(ws.recv(timeout=12))
                assert message["id"]==id,(id,message["id"])
                if message["type"] in wanted:
                    return message
                if message["type"]!="bus_audio":
                    raise ValueError(str(message))
        try:
            if a.live_queue:
                queue=a.live_queue
                for _ in range(3000):
                    if (queue/"rate").exists(): break
                    time.sleep(.1)
                rate=int((queue/"rate").read_text())
                def packets():
                    i=0
                    while True:
                        pcm=queue/f"{i:06}.pcm"
                        if pcm.is_file():
                            yield pcm.read_bytes()
                            i+=1
                        elif (queue/"end").is_file() and i==int((queue/"end").read_text()):
                            break
                        else:
                            if time.perf_counter()-start>150: raise TimeoutError("Native stream stalled")
                            time.sleep(.008)
                cases=["native-unchecked-preview"]
            else:
                with wave.open(str(a.wav),"rb") as wav:
                    assert wav.getsampwidth()==2 and wav.getnchannels()==1
                    rate=wav.getframerate()
                    data=wav.readframes(wav.getnframes())
                cases=["complete","cancel","broken-sequence","recover"]
                def packets():
                    size=int(rate*.04)*2
                    for i in range(0,len(data),size):
                        yield data[i:i+size]
            for case in cases:
                start=time.perf_counter()
                send(case,{"type":"start","rate":rate})
                event(case,{"ready"})
                ready=(time.perf_counter()-start)*1000
                frames=0
                status="finished"
                for i,block in enumerate(packets()):
                    if not a.live_queue:
                        time.sleep(max(0,start+max(0,i-2)*.04-time.perf_counter()))
                    # Transport packet size is independent of the native yield size.
                    for k in range(0,len(block),32768):
                        if k==0 and i==0:
                            seq=0
                        send(case,pcm_message(seq,block[k:k+32768]))
                        seq+=1
                    frames+=len(block)//2
                    if case=="cancel" and i==9:
                        send(case,{"type":"cancel"})
                        status="interrupted"
                        break
                    if case=="broken-sequence" and i==0:
                        send(case,pcm_message(seq+1,block))
                        status="failed"
                        break
                if status=="finished":
                    send(case,{"type":"end","frames":frames})
                # Receiver stamps the first nonzero at the sink; late host reading
                # never turns into a purported first-sound timestamp.
                message=event(case,{status})
                assert message["frames"]==frames and (status!="finished" or message["heard_on_bus"])
                rows.append({"case":case,"localhost_start_ready_roundtrip_ms":round(ready,3),
                             "total_to_terminal_ms":round((time.perf_counter()-start)*1000,3),"terminal":message})
                send(case,pcm_message(seq,b"\0\0"))
                send(case,{"type":"start","rate":rate})
                assert event(case,{status})==message
            send("",{"type":"quit"})
        except Exception as exc:
            failures.append(type(exc).__name__+": "+str(exc)[:250])
        finally:
            done.set()
    with serve(handle,"127.0.0.1",0) as server:
        port=server.socket.getsockname()[1]
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        env=dict(os.environ,TTS_BENCH_PORT=str(port),ANIME_AGENT_SPEECH_GAIN_DB="5")
        command=[str(a.godot),"--display-driver","headless","--audio-driver","WASAPI","--max-fps","120",
                 "--path",str(a.project),"--log-file",str(a.project.parent/"stream-godot.log"),
                 "--script",str(Path(__file__).with_name("stream_sink.gd"))]
        with subprocess.Popen(command,env=env,creationflags=subprocess.CREATE_NO_WINDOW) as child:
            try:
                if not done.wait(340 if a.live_queue else 35):
                    failures.append("no terminal receipt before deadline")
                if failures and child.poll() is None:
                    child.terminate()
                child.wait(timeout=5)
            finally:
                if child.poll() is None:
                    child.kill()
        server.shutdown()
    a.output.write_text(json.dumps({"rows":rows,"failures":failures},indent=2)+"\n",encoding="utf8")
    print("WS bench",len(rows),failures)
    return int(bool(failures))

if __name__=="__main__":
    p=argparse.ArgumentParser()
    src=p.add_mutually_exclusive_group(required=True)
    src.add_argument("--wav",type=Path)
    src.add_argument("--live-queue",type=Path)
    for key in ["godot","project","output"]:
        p.add_argument("--"+key,type=Path,required=True)
    raise SystemExit(run(p.parse_args()))
