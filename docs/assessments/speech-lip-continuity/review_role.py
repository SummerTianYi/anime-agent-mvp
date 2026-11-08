"""Summarize the actual mesh trace and encode private window-only footage."""
import argparse
import csv
import json
from pathlib import Path
import statistics
import subprocess
import wave

p=argparse.ArgumentParser()
p.add_argument("video",type=Path)
p.add_argument("ffmpeg",type=Path)
p.add_argument("output",type=Path)
a=p.parse_args()
report={}
mesh_rows=[]
for name in ("before","after"):
    d=a.video/name
    trace=json.loads((d/"trace.json").read_text(encoding="utf8"))
    rows=trace["samples"]
    mesh_rows.extend([name, *r] for r in rows)
    shots=trace["shots"]
    lines=["ffconcat version 1.0"]
    for i,ms in enumerate(shots):
        length=(shots[i+1]-ms)/1000 if i+1<len(shots) else .066
        lines.extend([f"file '{i:04d}.jpg'",f"duration {length:.4f}"])
    lines.append(f"file '{len(shots)-1:04d}.jpg'")
    (d/"frames.txt").write_text("\n".join(lines)+"\n",encoding="ascii")
    dst=d/"role.mp4"
    subprocess.run([str(a.ffmpeg),"-hide_banner","-loglevel","error","-y","-f","concat","-safe","0","-i","frames.txt",
                    "-i","window-audio.wav","-af",f"atrim=start={shots[0]/1000:.4f},asetpts=PTS-STARTPTS","-pix_fmt","yuv420p",
                    "-c:v","libx264","-preset","veryfast","-threads","2","-c:a","aac","-shortest",str(dst)],cwd=d,check=True)
    assert trace["avatar_bones"]==703 and trace["shapes"]==48 and trace["driver"]=="WASAPI"
    mouth={phase:round(max(r[2] for r in rows if r[1]==phase),4) for phase in ["wait","gap","cancelled","failed"]}
    silent=[r for r in rows if r[1]=="file" and 1.85<r[4]<2.17]
    voiced=[r for r in rows if r[1]=="file" and r[3]>.04]
    assert len(silent)>=4 and max(r[3] for r in silent)<.002 and len(voiced)>6
    result=dict(frames=len(rows),rendered_images=len(shots),bones=703,expressions=48,driver=trace["driver"],
                max_jaw_in_quiet_phases=mouth,silent_frames=len(silent),internal_silence_max_jaw=max(r[2] for r in silent),
                voiced_max_jaw=max(r[2] for r in voiced),voiced_median_jaw=statistics.median(r[2] for r in voiced),
                blink_peak=max(r[5] for r in rows),smile_peak=max(r[6] for r in rows),
                receipts=trace["receipts"],resources=json.loads((d/"resources.json").read_text()))
    report[name]=result
    assert result["blink_peak"]>.1 and result["smile_peak"]>.1
    assert max(mouth.values()) > .4 if name=="before" else max(mouth.values()) < .001
    assert result["internal_silence_max_jaw"] > .4 if name=="before" else result["internal_silence_max_jaw"] < .001
    assert result["voiced_max_jaw"]>.3
a.output.write_text(json.dumps(report,indent=2)+"\n",encoding="utf8")
with a.output.with_name("mesh.tsv").open("w",encoding="utf8",newline="") as out:
    writer=csv.writer(out,delimiter="\t",lineterminator="\n")
    writer.writerow(["version","elapsed_ms","phase","jaw","bus_peak","player_sec","blink","smile"])
    writer.writerows(mesh_rows)
