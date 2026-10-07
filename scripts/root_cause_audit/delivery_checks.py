"""Codex: audit-package checks in isolated env, no production API or business writes."""
import argparse,ast,json,os,subprocess,sys,tempfile
from pathlib import Path
from probe import ROOT,save
p=argparse.ArgumentParser();p.add_argument('--label',default='delivery-checks');a=p.parse_args()
results=[]
for file in (ROOT/'scripts/root_cause_audit').glob('*.py'):
    ast.parse(file.read_text(encoding='utf-8'))
results.append({'check':'audit_python_syntax','passed':True})
with tempfile.TemporaryDirectory(prefix='tianyi-audit-doccheck-') as tmp:
    env={k:v for k,v in os.environ.items() if not k.startswith(('ANIME_AGENT_','LLM_','GLM_','DEEPSEEK_'))}
    env.update(PYTHONUTF8='1',ANIME_AGENT_CONFIG_PATH=str(Path(tmp)/'absent.env'),
        ANIME_AGENT_DATA_DIR=tmp,ANIME_AGENT_TTS='0',ANIME_AGENT_WAKE_WORD='0',
        ANIME_AGENT_MCP_SERVERS='',LLM_PROVIDER='mock')
    for cmd in ([sys.executable,'scripts/check_docs_consistency.py'],
                [sys.executable,'-m','unittest','discover','-s','scripts/root_cause_audit','-p','test_*.py']):
        r=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8',timeout=120)
        results.append({'check':' '.join(cmd[1:]),'passed':r.returncode==0,
            'output':(r.stdout+r.stderr).replace(tmp,'<TEMP>').replace(str(ROOT),'<SOURCE>')})
pkg=ROOT/'docs/assessments/root-cause-audit'
rows=json.loads((pkg/'coverage.json').read_text(encoding='utf-8'))
assert len({r['id'] for r in rows})==len(rows)
missing=[]
for row in rows:
    for ev in row['evidence'].split(';'):
        if ev.strip() and not (pkg/ev.strip()).is_file():missing.append({'id':row['id'],'path':ev})
results.append({'check':'coverage_ids_and_evidence','passed':not missing,'missing':missing,'count':len(rows)})
changed=subprocess.check_output(['git','diff','--name-only','acc7bd4227c8e99a4adb7ed7266a8e1d06105ebd','--','docs/assessments/harness-v0','docs/assessments/harness-v1','services/agent-core','apps/avatar-runtime'],cwd=ROOT).decode().splitlines()
results.append({'check':'business_and_frozen_evidence_unchanged','passed':not changed,'changes':changed})
out={'layer':'offline delivery checks','api_calls':0,'results':results,'passed':all(r['passed'] for r in results)}
save(a.label,out)
print(json.dumps(out,ensure_ascii=False,indent=2))
raise SystemExit(not out['passed'])
