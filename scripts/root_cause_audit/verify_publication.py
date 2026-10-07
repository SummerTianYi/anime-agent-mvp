"""Read-only verification of staged/committed publication; no credentials printed."""
import argparse,ast,hashlib,json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser();p.add_argument('--production',type=Path,required=True);p.add_argument('--ref');a=p.parse_args()
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def blob(path):return git('show',(a.ref+':' if a.ref else ':')+path)
files=git('diff','--name-only','-z',*([a.ref+'^',a.ref] if a.ref else ['--cached'])).decode().split('\0')
files=[f for f in files if f]
allowed=('docs/assessments/root-cause-audit/','scripts/root_cause_audit/')
extra={'README.md','docs/HANDOFF.md','docs/CONTRIBUTIONS.md','docs/plans/README.md'}
assert all(f in extra or f.startswith(allowed) for f in files), 'Unexpected staged scope'
secrets=[]
for line in (a.production/'.env').read_text(encoding='utf-8-sig').splitlines():
    k,sep,v=line.partition('=')
    v=v.strip().strip('\"').strip("'")
    if sep and not k.startswith('#') and len(v)>8 and any(x in k.upper() for x in ('KEY','TOKEN','SECRET','PASSWORD')):secrets.append(v.encode())
total=0
for f in files:
    data=blob(f);total+=len(data)
    assert len(data)<50*1024*1024, 'Oversized staged file'
    assert not any(s in data for s in secrets), 'Secret-value match; value withheld'
    assert not re.search(rb'(?:sk-sp-|ghp_|gho_|AIzaSy)[A-Za-z0-9_.-]{16,}',data), 'Token-shaped match; value withheld'
    if f.endswith('.json'):json.loads(data)
    if f.endswith('.py'):ast.parse(data.decode())
base='docs/assessments/root-cause-audit/'
m=json.loads(blob(base+'publication-manifest.json'))
for item in m['files']:
    assert hashlib.sha256(blob(base+item['path'])).hexdigest()==item['published_sha256'], item['path']
d=json.loads(blob(base+'evidence/ledger.json'))
assert sum(d['by_provider'].values())==d['observed_http_attempts']==54
assert len({v['call_id'] for v in d['calls']})==d['distinct_http_calls']
coverage=json.loads(blob(base+'coverage.json'))
assert len(coverage)==len({r['id'] for r in coverage})==256
print(json.dumps({'status':'PASS','scope_files':len(files),'bytes':total,'verified_public_hashes':len(m['files']),
    'observed_model_http':54,'coverage_entries':256,'secret_scan':'no current credential values or token-shaped strings found'},ensure_ascii=False))
