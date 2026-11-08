"""Offline check of the published measurements. No audio, model, database or network needed."""
import json
from pathlib import Path
from statistics import median

here=Path(__file__).resolve().parent
def read(name):
    return json.loads((here/name).read_text(encoding="utf8"))

ds=read("deepseek.json")
assert ds["actual_ds_attempts"]==6
handoffs=[]
for k,r in ds["rows"].items():
    assert r["tts_entries"][0]["id"]==k and len(r["ds"])==1 and r["ds"][0]["model"]=="deepseek-flash"
    assert r["ds"][0]["end_ms"]<=r["chat_response_ms"]<=r["tts_entries"][0]["ms"]
    handoffs.append(r["tts_entries"][0]["ms"])
wav=read("playback.json")
assert wav["driver"]=="WASAPI" and not wav["failures"] and len(wav["measurements"])==7
assert all(r["bus_first_ms"]>0 for r in wav["measurements"])
gaps=[]
for name in ("gaps.json","gaps-shortened.json"):
    data=read(name)
    runs=data["measurements"]
    assert [(r["parts"],r["repeat"]) for r in runs]==[(2,0),(2,1),(4,0),(4,1)]
    intervals=[x for r in runs for x in r["interpart_last_to_first_nonzero_ms"]]
    assert not data["failures"] and len(intervals)==8 and min(intervals)>0
    gaps.append(median(intervals))
assert read("pause-fixture.json")["prefix_identical"]
for name in ("ws-playback.json","ws-timed.json"):
    msg=read(name)
    assert not msg["failures"]
    assert [r["terminal"]["type"] for r in msg["rows"]]==["finished","interrupted","failed","finished"]
    assert msg["rows"][0]["terminal"]["frames"]==msg["rows"][-1]["terminal"]["frames"]==101760
    assert not msg["rows"][2]["terminal"]["heard_on_bus"]
print("Evidence OK. Handoff ms",min(handoffs),max(handoffs),"interpart ms",*gaps)
