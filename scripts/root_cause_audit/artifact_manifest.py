"""Codex: hash runtime assets and only the named synthetic audit fixtures."""
import argparse,json,hashlib
from datetime import datetime,timezone
from pathlib import Path
from probe import save
p=argparse.ArgumentParser();p.add_argument('--production',type=Path,required=True);p.add_argument('--label',required=True);a=p.parse_args()
def inspect(relative):
    path=a.production/relative
    if not path.is_file():return {'path':relative,'exists':False}
    digest=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):digest.update(chunk)
    return {'path':relative,'exists':True,'bytes':path.stat().st_size,'sha256':digest.hexdigest()}
expected={'apps/avatar-runtime/assets/luotianyi_v4.glb':('df55806d343d149b41c20d0ef074373cafca2379212fd8691e998ea6cddc6e4a',128621144),'apps/avatar-runtime/assets/motions/luotianyi_idle.glb':('5cf15a1d3e657cf76e5f58e33c9d3593a14494b89817ad2a910d57cabf9d433a',23070740),'apps/avatar-runtime/assets/motions/luotianyi_pirouette.glb':('1fefbf0667711845e4fc6e0574d57d74c8982e15aa76a2a25bb9192be1faa284',23114580)}
registry=json.loads((a.production/'apps/avatar-runtime/motion_registry.json').read_text(encoding='utf-8'))
paths=set(expected)|{'apps/avatar-runtime/'+r['path'].removeprefix('res://') for r in registry['clips']}
assets=[]
for path in sorted(paths):
    row=inspect(path)
    if path in expected: row['matches_frozen_contract']=(row.get('sha256'),row.get('bytes'))==expected[path]
    assets.append(row)
fixtures=[]
for name in ('source-a.txt','source-b.txt','result.txt','control.txt','twin-a.txt','twin-b.txt','twin-c.txt'):
    rel='work/tianyi-notes/root-cause-audit-20261007/'+name;row=inspect(rel)
    if row['exists']:row['synthetic_content']=(a.production/rel).read_text(encoding='utf-8')
    fixtures.append(row)
out={'utc':datetime.now(timezone.utc).isoformat(),'layer':'passive artifact inspection, not visual acceptance','assets':assets,'fixtures':fixtures,'timing':'post frontend tasks; initial source-a/b lacked separately hashed pre-state; twin targets pre-state directory listing contained only source-a/b','api_calls':0}
save(a.label,out);print(json.dumps(out,ensure_ascii=False,indent=2))
