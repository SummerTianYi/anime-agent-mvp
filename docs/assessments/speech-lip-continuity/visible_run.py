"""Run the cached role in an independent visible Godot and guard only our child process."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time
import psutil

p=argparse.ArgumentParser()
for key in ("godot","project","wav","output"):
    p.add_argument("--"+key,type=Path,required=True)
a=p.parse_args()
assert (a.project/"project.godot").read_text(encoding="utf8").find("Tianyi private lipsync lab")>=0
a.output.mkdir(exist_ok=True)
assert not (a.output/"trace.json").exists()
available=psutil.virtual_memory().available
if available < 1100*1024**2:
    raise SystemExit("Insufficient headroom for the cached avatar (observed peak 520 MiB)")
env=dict(os.environ,LIP_TRACE=str(a.output),LIP_WAV=str(a.wav),ANIME_AGENT_SPEECH_GAIN_DB="5",AGENT_CORE_WS_URL="ws://127.0.0.1:1")
binary=a.godot.with_name(a.godot.name.replace("_console.exe",".exe"))
cmd=[str(binary),"--path",str(a.project),"--rendering-method","gl_compatibility","--max-fps","30","--audio-driver","WASAPI",
     "--log-file",str(a.output/"engine.log"),"--script",str(Path(__file__).with_name("role_probe.gd"))]
peak=0
minimum=available
start=time.monotonic()
with (a.output/"launch.log").open("wb") as log,subprocess.Popen(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW) as proc:
    child=psutil.Process(proc.pid)
    try:
        while proc.poll() is None:
            free=psutil.virtual_memory().available
            minimum=min(minimum,free)
            try:
                peak=max(peak,child.memory_info().rss)
            except psutil.NoSuchProcess:
                break
            if free<450*1024**2 or time.monotonic()-start>45:
                proc.terminate()
                raise RuntimeError("Isolated child stopped by resource/time guard")
            time.sleep(.2)
        if proc.wait() or not (a.output/"trace.json").exists():
            raise RuntimeError("Trace unavailable; inspect private launch.log")
    finally:
        if proc.poll() is None:
            proc.terminate()
        (a.output/"resources.json").write_text(json.dumps(dict(initial=available,minimum=minimum,child_peak=peak)),encoding="utf8")
