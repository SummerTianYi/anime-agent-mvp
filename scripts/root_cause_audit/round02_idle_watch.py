"""Read-only real Windows inactivity samples; no clock/input/service mutations."""
import argparse
import ctypes
from datetime import datetime, timezone
import json
from pathlib import Path
import time

p=argparse.ArgumentParser()
p.add_argument("--output",type=Path,required=True)
p.add_argument("--deadline-seconds",type=int,default=900)
a=p.parse_args()
if a.output.exists():
    raise SystemExit("Output exists")
class LastInput(ctypes.Structure):
    _fields_=[("cbSize",ctypes.c_uint),("dwTime",ctypes.c_uint)]
started=time.monotonic()
samples=[]
while time.monotonic()-started<a.deadline_seconds:
    info=LastInput(ctypes.sizeof(LastInput),0)
    if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
        raise ctypes.WinError()
    now_tick=ctypes.windll.kernel32.GetTickCount() & 0xffffffff
    idle=((now_tick-info.dwTime)&0xffffffff)/1000
    samples.append({"utc":datetime.now(timezone.utc).isoformat(),"elapsed":round(time.monotonic()-started,3),"idle_seconds":idle,"last_input_tick":info.dwTime})
    if idle>=670:
        break
    time.sleep(5)
report={"layer":"real Windows GetLastInputInfo, no simulated time/input", "samples":samples,
        "observed_600":any(row["idle_seconds"]>=600 for row in samples),"observed_670":any(row["idle_seconds"]>=670 for row in samples)}
with a.output.open("x",encoding="utf-8") as file:
    json.dump(report,file,ensure_ascii=False,indent=2)
print(json.dumps({"samples":len(samples),"max_idle":max(row["idle_seconds"] for row in samples),"observed_600":report["observed_600"]}))
