"""Codex: V1 guard reuse, isolated project/data and no production Core."""
import argparse, json, os, shutil, subprocess, tempfile, time
from pathlib import Path
from probe import ROOT, save
p=argparse.ArgumentParser();p.add_argument('--production',type=Path,required=True)
p.add_argument('--label',default='godot-guards');p.add_argument('--only-speech',action='store_true');a=p.parse_args()
engine=a.production.parent/'tools/godot-4.7.2/Godot_v4.7.2-stable_win64_console.exe'
rows=[]
with tempfile.TemporaryDirectory(prefix='tianyi-root-audit-godot-') as temp:
    isolated=Path(temp);target=isolated/'apps/avatar-runtime'
    (isolated/'.farewell-test-fixture').write_text('Codex disposable audit fixture',encoding='utf-8')
    shutil.copytree(a.production/'apps/avatar-runtime', target,
                    ignore=shutil.ignore_patterns('.godot','assets','captures','*.log'))
    shutil.copytree(a.production/'apps/avatar-runtime/assets', target/'assets',
                    ignore=shutil.ignore_patterns('*.import'))
    env=os.environ.copy();env.update(AGENT_CORE_WS_URL='ws://127.0.0.1:1/ws',
        APPDATA=str(isolated/'roaming'),LOCALAPPDATA=str(isolated/'local'))
    scripts=(None,'verify_speech_delivery.gd') if a.only_speech else (None,'verify_text_input.gd',
        'verify_session_ui.gd','verify_effort_ui.gd','verify_tool_activity.gd',
        'verify_speech_delivery.gd','verify_farewell_speech.gd')
    for script in scripts:
        args=[str(engine),'--headless','--path',str(target)]
        args+=['--editor','--import','--quit'] if script is None else ['--script','res://'+script]
        start=time.monotonic()
        try:
            r=subprocess.run(args,env=env,capture_output=True,text=True,encoding='utf-8',timeout=120)
            output=(r.stdout+r.stderr).replace(str(isolated),'<ISOLATED>').replace(str(a.production),'<PRODUCTION>')
            rows.append({'script':script or 'import','exit_code':r.returncode,'output':output,
                         'passed':r.returncode==0 and 'SCRIPT ERROR' not in output and 'FAIL' not in output,
                         'seconds':round(time.monotonic()-start,3)})
        except subprocess.TimeoutExpired:
            rows.append({'script':script,'passed':False,'error':'120s timeout'})
        print(rows[-1]['script'],rows[-1]['passed'],flush=True)
save(a.label,{'layer':'isolated offline guard, NOT current desktop acceptance',
    'production_core_contacted':False,'api_calls':0,'rows':rows})
raise SystemExit(not all(r['passed'] for r in rows))
