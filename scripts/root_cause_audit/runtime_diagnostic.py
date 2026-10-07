"""Codex: passive lifecycle/auth metadata, no token or unrelated message output."""
import argparse,json,hashlib,sys,os
from datetime import datetime,timezone
from pathlib import Path
from probe import get,db_connect,save
p=argparse.ArgumentParser();p.add_argument('--production',type=Path,required=True);p.add_argument('--label',required=True);a=p.parse_args()
sys.path.insert(0,str(a.production.parent/'tianyi-tts/venv/Lib/site-packages'))
import psutil
out={'utc':datetime.now(timezone.utc).isoformat(),'layer':'passive diagnostic, not frontend acceptance'}
for port in (8765,8770):
    try:out[str(port)]=get(port,'/health')
    except Exception as e:out[str(port)]={'error':str(e)}
cred=Path.home()/'.gmail-mcp/credentials.json'
if cred.exists():
    data=json.loads(cred.read_text());old=a.production/'runs/private-audit-preservation/gmail-before-auth-20261007-194000/credentials.json'
    out['gmail_auth']={'modified_utc':datetime.fromtimestamp(cred.stat().st_mtime,timezone.utc).isoformat(),'changed_since_backup':old.exists() and old.read_bytes()!=cred.read_bytes(),'access_token_present':bool(data.get('access_token')),'refresh_token_present':bool(data.get('refresh_token')),'token_values':'not collected'}
out['processes']=[]
for proc in psutil.process_iter(['pid','ppid','name','create_time']):
    try:
        argv=proc.cmdline();cmd=' '.join(argv)
        tags=[s for s in ('agent_core.main','Godot_v4.7.2','tts_server.py','watch-tts-session.ps1','core_watchdog.ps1','server-gmail-autoauth-mcp') if s in cmd]
        if not tags:continue
        out['processes'].append({**proc.info,'tags':tags,'cwd':proc.cwd()})
    except psutil.Error:pass
local=str(Path(os.environ['LOCALAPPDATA'])/'AnimeAgent/logs')
logs=Path('\\\\localhost\\'+local[0].lower()+'$\\'+local[3:])
out['watch_events']=[]
f=logs/'tts-watch.log'
if f.exists():
    for line in f.read_text(encoding='utf-8-sig',errors='replace').splitlines()[-100:]:
        try:
            row=json.loads(line)
            if row.get('time','')>='2026-10-07T18:00:00':out['watch_events'].append(row)
        except ValueError:pass
out['sidecar_error_lines']=[]
for f in sorted(logs.glob('tts-*.stderr.log'),key=lambda p:p.stat().st_mtime,reverse=True)[:3]:
    lines=[s for s in f.read_text(encoding='utf-8',errors='replace').splitlines()[-160:] if any(k in s for k in ('Error','error','Exception','Traceback','CUDA','Memory','WinError','failed'))]
    out['sidecar_error_lines'].append({'file':f.name,'lines':lines})
out['sidecar_status_lines']=[]
for f in sorted(logs.glob('tts-*.stdout.log'),key=lambda p:p.stat().st_mtime,reverse=True)[:6]:
    lines=[s for s in f.read_text(encoding='utf-8',errors='replace').splitlines() if s.startswith(('TTS_SYNTH_FAILED','TTS_SERVER_LOAD_FAILED','TTS_SERVER_READY','TTS_SYNTH_OK'))]
    out['sidecar_status_lines'].append({'file':f.name,'lines':lines[-45:]})
if isinstance(out.get('8765'),dict) and 'memory' in out['8765']:
    db=db_connect(out['8765']);out['stable_copy_quick_check']=[r[0] for r in db.execute('PRAGMA quick_check')]
    out['db_latest_ids']={t:db.execute('SELECT MAX(id) FROM '+t).fetchone()[0] for t in ('messages','events')}
    out['8765'].pop('memory',None)
text=json.dumps(out,ensure_ascii=False).replace(str(a.production),'<PRODUCTION>').replace(str(a.production.parent),'<WORK>').replace(str(Path.home()),'<USER>')
out=json.loads(text);save(a.label,out);print(json.dumps(out,ensure_ascii=False,indent=2))
