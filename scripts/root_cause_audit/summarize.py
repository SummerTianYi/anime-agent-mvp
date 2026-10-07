"""Codex: consolidate already-captured audit evidence; zero network/production writes."""
import argparse, hashlib, json, subprocess
from collections import Counter
from pathlib import Path
from probe import ROOT, OUT, save

p=argparse.ArgumentParser();p.add_argument('--production',type=Path,required=True);a=p.parse_args()
calls={};messages={};actions={};sessions={};events={}
for file in sorted(OUT.glob('desktop-*.json')):
    d=json.loads(file.read_text(encoding='utf-8'));sid=d['session_id']
    sessions[sid]=file.name
    for m in d['messages']:messages[(sid,m['id'])]=m
    for action in d['actions']:actions[action['action_id']]=action
    for e in d['events']:
        key=(e['id'],e['event_type'],e['created_at'])
        events[key]=e
        if e['event_type']=='provider.transport':
            v=e['payload'];ident=v['call_id'];old=calls.get(ident)
            if old is None or v['attempt']>=old['attempt']:
                calls[ident]={**v,'session_id':sid,'evidence':file.name}
by_provider=Counter()
for call in calls.values():by_provider[call['provider']]+=call['attempt']
requests=sorted({m['request_id'] for m in messages.values() if m['role']=='user'})
receipts=[dict(event_id=e['id'],type=e['event_type'],time=e['created_at'],payload=e['payload'])
          for e in events.values() if e['event_type'].startswith(('tts.','speech.','audio.'))]
save('ledger',{'layer':'derived from passive desktop captures; no model requests',
    'method':'union call_id; max attempt; never sum cumulative snapshots',
    'hard_limit':180,'observed_http_attempts':sum(by_provider.values()),
    'by_provider':dict(by_provider),'distinct_http_calls':len(calls),
    'unique_user_requests':len(requests),'request_ids':requests,
    'sessions_latest_evidence':sessions,'calls':list(calls.values()),
    'actions_latest':list(actions.values()),
    'accounting_limits':'Only well-formed, request-associated provider.transport events are countable. Historical malformed events exist; this is an observed count, not provider billing proof. Title is requested in the same chat call by current main.py, not a separate title endpoint.',
    'audio_events':receipts})
before=json.loads((OUT/'runtime-start.json').read_text(encoding='utf-8'))
after=json.loads((OUT/'runtime-final.json').read_text(encoding='utf-8'))
diff=[k for k,v in before['files'].items() if k not in after['files'] or v['deployed_sha256']!=after['files'][k]['deployed_sha256']]
env=a.production/'.env';backup=a.production/'runs/private-audit-preservation/provider-env-before-glm-20261007/.env'
v01={}
for base in ('docs/assessments/harness-v0','docs/assessments/harness-v1'):
    data=subprocess.check_output(['git','diff','--name-only','acc7bd4227c8e99a4adb7ed7266a8e1d06105ebd','--',base],cwd=ROOT).decode()
    v01[base]={'changed_tracked_files':data.splitlines()}
save('restoration',{'runtime_manifest_changed_files':diff,
    'production_tracked_status_unchanged':before['production_status']==after['production_status'],
    'production_git_head_unchanged':before['production_git_head']==after['production_git_head'],
    'formal_prompt_unchanged':before['prompt_sha256']==after['prompt_sha256'],
    'env_equal_private_pre_glm_backup':env.read_bytes()==backup.read_bytes(),
    'env_sha256':hashlib.sha256(env.read_bytes()).hexdigest(),
    'active_model':after['health']['llm'],'historical_evidence':v01,
    'not_proven':'No claim of all user-data bytes unchanged: authorized synthetic messages/facts and runtime event writes are expected. No user-history deletion/migration/repair was performed.'})
print(json.dumps({'http':dict(by_provider),'total':sum(by_provider.values()),'requests':len(requests),'sessions':len(sessions),'actions':len(actions),'manifest_changed':diff,'env_restored':env.read_bytes()==backup.read_bytes()},ensure_ascii=False))
