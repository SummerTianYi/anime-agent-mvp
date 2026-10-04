"""Isolated Godot guards using a temporary copy of local-only assets."""
import json, os
from pathlib import Path
import shutil, subprocess, sys, tempfile, time
ROOT=Path(__file__).resolve().parents[2]
production=Path(sys.argv[1]).resolve()
engine=production.parent/"tools/godot-4.7.2/Godot_v4.7.2-stable_win64_console.exe"
if not engine.exists(): engine=production.parent.parent/"tools/godot-4.7.2/Godot_v4.7.2-stable_win64_console.exe"
rows=[]
with tempfile.TemporaryDirectory(prefix="tianyi-v1-godot-") as directory:
    target=Path(directory)/"avatar"
    shutil.copytree(ROOT/"apps/avatar-runtime",target,ignore=shutil.ignore_patterns(".godot","assets","captures","*.log"))
    shutil.copytree(production/"apps/avatar-runtime/assets",target/"assets",ignore=shutil.ignore_patterns("*.import"))
    env=os.environ.copy();env["AGENT_CORE_WS_URL"]="ws://127.0.0.1:1/ws"
    for script in (None,"verify_text_input.gd","verify_session_ui.gd","verify_effort_ui.gd","verify_tool_activity.gd"):
        args=[str(engine),"--headless","--path",str(target)]
        args+=["--editor","--import","--quit"] if script is None else ["--script","res://"+script]
        try:
            result=subprocess.run(args,env=env,capture_output=True,text=True,encoding="utf-8",timeout=90)
            output=(result.stdout+result.stderr).replace(str(target),"{ISOLATED_AVATAR}").replace(str(production),"{PRODUCTION}")
            rows.append(dict(script=script or "import",exit_code=result.returncode,
                passed=result.returncode==0 and "SCRIPT ERROR" not in output and "FAIL" not in output,output=output))
        except subprocess.TimeoutExpired:
            rows.append(dict(script=script,passed=False,error="timeout"))
        print(rows[-1]["script"],rows[-1]["passed"],flush=True)
out=ROOT/"docs/assessments/harness-v1/evidence"/("godot-"+str(time.time_ns())+".json")
out.write_text(json.dumps({"isolated":True,"production_core_contacted":False,"rows":rows},ensure_ascii=False,indent=2),encoding="utf-8")
print(out.relative_to(ROOT))
raise SystemExit(not all(r["passed"] for r in rows))
