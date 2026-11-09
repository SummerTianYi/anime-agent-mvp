"""Run the affected full-scene Godot gates in a disposable asset copy."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
from checks import ROOT

GATES = {"verify_text_input":"GODOT_CHAT_SHORTCUT_GUARD_OK","verify_session_ui":"GODOT_SESSION_UI_OK",
         "verify_tool_activity":"GODOT_TOOL_ACTIVITY_OK","verify_effort_ui":"GODOT_EFFORT_UI_OK",
         "verify_speech_delivery":"SPEECH_DELIVERY_REGRESSION"}


def run(args):
    args.out.mkdir(parents=True,exist_ok=False)
    glb = args.assets/"luotianyi_v4.glb"
    with glb.open("rb") as src:
        fingerprint = hashlib.file_digest(src,"sha256").hexdigest()
    assert fingerprint=="df55806d343d149b41c20d0ef074373cafca2379212fd8691e998ea6cddc6e4a"
    with tempfile.TemporaryDirectory(prefix="tianyi-query-gates-") as tmp, socket.socket() as port:
        port.bind(("127.0.0.1",0))  # Own the unreachable endpoint throughout all offline gates.
        project = Path(tmp)/"apps/avatar-runtime"
        (Path(tmp)/".farewell-test-fixture").touch()
        shutil.copytree(ROOT/"apps/avatar-runtime",project,ignore=shutil.ignore_patterns(".godot","assets"))
        shutil.copytree(args.assets,project/"assets")
        env = {k:v for k,v in os.environ.items() if not k.startswith(("ANIME_AGENT_","LLM_","TTS_","GODOT_"))
               and not any(x in k for x in ("TOKEN","KEY","SECRET","PASSWORD"))}
        env.update(APPDATA=tmp,LOCALAPPDATA=tmp,USERPROFILE=tmp,AGENT_CORE_WS_URL=f"ws://127.0.0.1:{port.getsockname()[1]}/ws",
                   ANIME_AGENT_TTS="0",ANIME_AGENT_WAKE_WORD="0",ANIME_AGENT_PROACTIVE="0")
        command=[str(args.godot),"--headless","--audio-driver","Dummy","--path",str(project)]
        stats = []
        for name,options in [("import",["--import"])]+[(g,["--script","res://"+g+".gd"]) for g in GATES]:
            result=subprocess.run(command+options,env=env,capture_output=True,timeout=190)
            log=(result.stdout+result.stderr).decode("utf8","replace")
            (args.out/(name+".txt")).write_text(log,encoding="utf8")
            passed=result.returncode==0 and (name=="import" or GATES[name] in log) and "SCRIPT ERROR" not in log
            stats.append({"gate":name,"exit":result.returncode,"marker":GATES.get(name),"passed":passed})
        (args.out/"gates.json").write_text(json.dumps({"model":fingerprint,"gates":stats},indent=2),encoding="utf8")
        print(stats)
        return all(s["passed"] for s in stats)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("godot","assets","out"):
        p.add_argument(name,type=Path)
    raise SystemExit(0 if run(p.parse_args()) else 1)
