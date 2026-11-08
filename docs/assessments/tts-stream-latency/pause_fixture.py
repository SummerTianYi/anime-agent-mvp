"""Private bench copy: shorten exact digital silence at the end of a synthesized WAV."""
import argparse
from array import array
import hashlib
import json
from pathlib import Path
import sys
import wave

def main():
    p=argparse.ArgumentParser()
    p.add_argument("synthesized_wav",type=Path)
    p.add_argument("new_wav",type=Path)
    p.add_argument("metrics",type=Path)
    a=p.parse_args()
    if a.new_wav.exists():
        p.error("Fresh private WAV output required")
    with wave.open(str(a.synthesized_wav),"rb") as r:
        params=r.getparams()
        assert params.nchannels==1 and params.sampwidth==2 and params.comptype=="NONE"
        original=r.readframes(r.getnframes())
    pcm=array("h",original)
    if sys.byteorder!="little":
        pcm.byteswap()
    last=next((i for i in range(len(pcm)-1,-1,-1) if pcm[i]!=0),None)
    assert last is not None
    zeros=len(pcm)-last-1
    remove=min(round(0.2*params.framerate),max(0,zeros-round(0.1*params.framerate)))
    assert remove>0
    kept=original[:-2*remove]
    assert not any(original[len(kept):])
    with wave.open(str(a.new_wav),"wb") as w:
        w.setparams(params)
        w.writeframes(kept)
    with wave.open(str(a.new_wav),"rb") as r:
        assert r.readframes(r.getnframes())==original[:len(kept)]
    values={"rate":params.framerate,"original_frames":len(pcm),"exact_trailing_zero_ms":zeros/params.framerate*1000,
            "removed_zero_ms":remove/params.framerate*1000,"prefix_identical":True,
            "original_pcm_sha256":hashlib.sha256(original).hexdigest(),"retained_pcm_sha256":hashlib.sha256(kept).hexdigest()}
    a.metrics.write_text(json.dumps(values,indent=2)+"\n",encoding="utf8")
    print(values)
if __name__=="__main__":
    main()
