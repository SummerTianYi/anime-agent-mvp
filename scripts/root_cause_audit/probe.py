"""Codex: read-only runtime snapshot; no Core imports, connector calls or DB writes."""
import argparse
import os
import re
import ast
import hashlib
import json
import sqlite3
import subprocess
import shutil
import tempfile
import atexit
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import ProxyHandler, build_opener
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(os.environ.get('ANIME_AUDIT_OUT', str(ROOT / 'docs/assessments/root-cause-audit/evidence')))

def sha(data):
    return hashlib.sha256(data).hexdigest()

def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args])

def get(port, suffix):
    with build_opener(ProxyHandler({})).open(f'http://127.0.0.1:{port}{suffix}', timeout=15) as r:
        return json.load(r)

def copy_stable_sqlite(source, dest):
    """Fail closed on file-set changes or a copy differing from either scan.

    This is a hash-checked passive file copy, NOT an atomic SQLite backup.
    We do not claim it proves absence of every possible filesystem race.
    """
    def manifest(base):
        return {ext: sha(Path(str(base)+ext).read_bytes())
                for ext in ('', '-wal') if Path(str(base)+ext).exists()}
    before = manifest(source)
    if '' not in before:
        raise RuntimeError('Source database not present')
    for ext in before:
        shutil.copyfile(Path(str(source)+ext), Path(str(dest)+ext))
    copied = manifest(dest)
    after = manifest(source)
    if not before == copied == after:
        raise RuntimeError('DB/WAL file set or hashes changed; reject snapshot')
    return {'source_before':before,'copy':copied,'source_after':after,
            'method':'passive file copy; equal file sets and SHA256 in three scans; not an atomic SQLite backup'}

LAST_SNAPSHOT = None

def db_connect(health):
    global LAST_SNAPSHOT
    reported=health['memory']['path']
    # Desktop Core is unpackaged. Packaged Codex sees an older redirected copy
    # at the same C: name; localhost's filesystem namespace targets the real file.
    physical='\\\\localhost\\'+reported[0].lower()+'$\\'+reported[3:]
    # SQLite UNC reads on this machine miss newer WAL rows. Copy both files
    # during a quiescent interval and require identical before/after hashes.
    temp=tempfile.TemporaryDirectory(prefix='tianyi-readonly-audit-')
    dest=Path(temp.name)/'view.sqlite3'
    try:
        LAST_SNAPSHOT = copy_stable_sqlite(physical, dest)
    except Exception:
        temp.cleanup()
        raise
    c = sqlite3.connect(dest.as_uri()+'?mode=ro', uri=True)
    def cleanup():
        c.close();temp.cleanup()
    atexit.register(cleanup)
    c.row_factory = sqlite3.Row
    c.execute('PRAGMA query_only=ON')
    return c

def save(name, data):
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / (name + '.json')
    if path.exists():
        raise SystemExit('Refusing to overwrite earlier evidence')
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

def snapshot(prod, label):
    h = get(8765, '/health')
    live = get(8765, '/health/live')
    db = db_connect(h)
    events = db.execute('SELECT coalesce(max(id),0) FROM events').fetchone()[0]
    starts = db.execute("SELECT id,payload,created_at FROM events WHERE event_type='mcp.started' ORDER BY id DESC LIMIT 1").fetchall()
    paths = sorted((prod/'services/agent-core/agent_core').rglob('*.py'))
    paths += sorted((prod/'services/agent-core/agent_core/data').glob('*.json'))
    paths += sorted((prod/'apps/avatar-runtime').glob('*.gd'))
    paths += sorted((prod/'scripts').glob('*tts*.ps1'))
    paths += [prod/'scripts/start-mvp.ps1',prod/'scripts/startup-common.ps1',prod/'start-anime-agent.cmd']
    manifest = {}
    for f in paths:
        if '__pycache__' in str(f) or not f.is_file():
            continue
        rel = f.relative_to(prod).as_posix()
        record = {'deployed_sha256':sha(f.read_bytes()),'mtime_utc':datetime.fromtimestamp(f.stat().st_mtime,timezone.utc).isoformat()}
        for ref in ('c212cba3622f6f2a7f008c6a8ad01e4f585a097b','acc7bd4227c8e99a4adb7ed7266a8e1d06105ebd'):
            try:
                data=git(ROOT,'show',ref+':'+rel)
                record[ref[:7]] = sha(data)
                record['matches_'+ref[:7]] = data.replace(b'\r\n',b'\n') == f.read_bytes().replace(b'\r\n',b'\n')
            except subprocess.CalledProcessError:
                record['matches_'+ref[:7]] = None
        manifest[rel]=record
    allowed={'LLM_PROVIDER','LLM_TIMEOUT_SECONDS','DEEPSEEK_MODEL','DEEPSEEK_BASE_URL','GLM_MODEL','GLM_BASE_URL','GLM_CREDENTIAL_SOURCE','ANIME_AGENT_VOICE_INPUT_MODE','ANIME_AGENT_WAKE_WORD','ANIME_AGENT_IDLE_THRESHOLD','ANIME_AGENT_QUIET_START','ANIME_AGENT_QUIET_END','ANIME_AGENT_TOOLS','ANIME_AGENT_VISION_MODEL','ANIME_AGENT_VISION_PROTOCOL'}
    cfg={}
    for line in (prod/'.env').read_text(encoding='utf-8-sig').splitlines():
        k,sep,v=line.partition('=')
        if sep and k in allowed: cfg[k]=v.strip()
    tree=ast.parse((prod/'services/agent-core/agent_core/harness.py').read_text(encoding='utf-8'))
    parts={n.targets[0].id:n.value.value for n in tree.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and isinstance(n.value,ast.Constant)}
    processes=[]
    try:
        import psutil
        core=psutil.Process(live['pid'])
        targets=[core]+core.children(recursive=True)
        targets += [p for p in psutil.process_iter(['name']) if 'godot' in (p.info['name'] or '').lower()]
        for p in targets:
            try: processes.append({'pid':p.pid,'ppid':p.ppid(),'name':p.name(),'created_utc':datetime.fromtimestamp(p.create_time(),timezone.utc).isoformat(),'executable_basename':Path(p.exe()).name})
            except psutil.Error: pass
    except ImportError: processes=[{'core_pid':live['pid'],'process_metadata':'psutil unavailable'}]
    sanitized={k:v for k,v in h.items() if k not in ('memory',)}
    sanitized['tts'].pop('service',None)
    mcp=[dict(r) for r in starts]
    for r in mcp: r['payload']=json.loads(r['payload'])
    record={'captured_utc':datetime.now(timezone.utc).isoformat(),'candidate_head':git(ROOT,'rev-parse','HEAD').decode().strip(),'production_git_head':git(prod,'rev-parse','HEAD').decode().strip(),'production_status':git(prod,'status','--porcelain').decode(),'health':sanitized,'liveness':live,'processes':processes,'config_allowlist':cfg,'prompt_sha256':sha((parts['ROLE_PROMPT']+'\n\n'+parts['RUNTIME_CONTRACT']).encode()),'files':manifest,'start_event_id':events,'last_mcp_start':mcp,'db_access':'read-only metadata; no message or fact contents queried','note':'Disk hashes are not direct in-memory code proof. Compare process start and file mtimes; no restart performed.'}
    save(label,record)
    print(json.dumps({k:record[k] for k in ('captured_utc','production_git_head','health','liveness','processes','config_allowlist','prompt_sha256','start_event_id','last_mcp_start')},ensure_ascii=False,indent=2))
    print('Runtime files mismatching c212:',[p for p,v in manifest.items() if v['matches_c212cba'] is False])

def capture(label, session=None, request=None):
    db=db_connect(get(8765,'/health'))
    if session is None:
        row=db.execute("SELECT conversation_id FROM messages WHERE content LIKE '%根因审计%' AND created_at>='2026-10-07' ORDER BY id DESC LIMIT 1").fetchone()
        if row is None:
            print('Health DB path:',get(8765,'/health')['memory']['path'])
            print('Recent message metadata only:',[tuple(r) for r in db.execute('SELECT id,role,request_id,conversation_id,created_at,length(content) FROM messages ORDER BY id DESC LIMIT 5')])
            print('Recent event metadata only:',[tuple(r) for r in db.execute('SELECT id,event_type,created_at FROM events ORDER BY id DESC LIMIT 10')])
            raise SystemExit('Audit session not found; do not use unrelated messages')
        session=row[0]
    allowed={r[0] for r in db.execute("SELECT request_id FROM messages WHERE conversation_id=? AND role='user' AND (content LIKE '%根因审计的独立测试会话%' OR content LIKE '[RA-%' OR content IN ('确认','不同意','取消','继续')) AND created_at>='2026-10-07 11:02:00'",(session,))}
    if request: allowed.add(request)
    messages=[dict(r) for r in db.execute('SELECT * FROM messages WHERE conversation_id=? ORDER BY id',(session,)) if r['request_id'] in allowed]
    ids={r['request_id'] for r in messages}
    if request: ids.add(request)
    all_events=[]
    invalid=[]
    malformed_count=db.execute('SELECT count(*) FROM events WHERE julianday(created_at) IS NULL').fetchone()[0]
    for r in db.execute("SELECT * FROM events WHERE julianday(created_at)>=julianday('2026-10-07 11:01:00') ORDER BY id"):
        try: payload=json.loads(r['payload'])
        except (ValueError,TypeError):
            invalid.append({'id':r['id'],'type':r['event_type'],'created_at':r['created_at'],'payload_type':type(r['payload']).__name__})
            continue
        all_events.append({**dict(r),'payload':payload})
    events=[r for r in all_events if r['payload'].get('request_id') in ids or r['payload'].get('requestId') in ids or r['payload'].get('session_id')==session]
    utterances={r['payload'].get('utteranceId') for r in events}-{None}
    events += [r for r in all_events if r not in events and r['payload'].get('utteranceId') in utterances]
    tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    actions=[]
    if 'harness_actions' in tables:
        actions=[json.loads(r['payload']) for r in db.execute('SELECT * FROM harness_actions WHERE session_id=?',(session,))]
    facts=[dict(r) for r in db.execute('SELECT * FROM facts WHERE session_id=?',(session,)) if r['source_request_id'] in ids]
    calls={}
    for r in events:
        if r['event_type']=='provider.transport':
            p=r['payload'];calls[p['call_id']]=max(calls.get(p['call_id'],0),p['attempt'])
    data={'session_id':session,'captured_utc':datetime.now(timezone.utc).isoformat(),'messages':messages,'events':sorted(events,key=lambda r:r['id']),'actions':actions,'facts':facts,'http_attempts_observed':sum(calls.values()),'wire_calls':calls,'layer':'current-desktop input; passive read-only database evidence','human_audio':'not confirmed','actual_wire_context':'not recorded by current production telemetry; do not infer exact wire body from reconstructed prompt'}
    data['unparseable_event_metadata']=invalid
    data['malformed_event_timestamp_rows_excluded']=malformed_count
    data['snapshot_verification']=LAST_SNAPSHOT
    def redact(s):
        s=re.sub(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', 'OWNER_TEST_MAILBOX', s)
        return s
    data=json.loads(redact(json.dumps(data,ensure_ascii=False)))
    save(label,data)
    action_summary=[{k:a.get(k) for k in ('action_id','tool','status','confirmation_request_id')} |
                    {'receipt_preview':str(a.get('receipt'))[:200]} for a in actions]
    print(json.dumps({'session':session,'latest_messages':messages[-4:],'actions':action_summary,'facts':facts,'http':sum(calls.values()),'evidence':label},ensure_ascii=False,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--production',type=Path)
    p.add_argument('--label',default='runtime-start')
    p.add_argument('--capture',action='store_true')
    p.add_argument('--session',type=int)
    p.add_argument('--request')
    a=p.parse_args()
    if a.capture: capture(a.label,a.session,a.request)
    else: snapshot(a.production,a.label)
