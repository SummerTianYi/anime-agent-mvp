"""Codex: passive configuration/source/dependency inventory, never start connectors."""
import argparse
import ast
import json
import re
import subprocess
from pathlib import Path
from probe import ROOT, get, db_connect, sha, save, git

p=argparse.ArgumentParser();p.add_argument('--production',type=Path,required=True);a=p.parse_args();prod=a.production
cfg={}
for line in (prod/'.env').read_text(encoding='utf-8-sig').splitlines():
    k,sep,v=line.partition('=')
    if sep and not k.startswith('#'):cfg[k.strip()]=v.strip().strip('"').strip("'")
safe={k:v for k,v in cfg.items() if k in {'ANIME_AGENT_TOOLS_ROOTS','ANIME_AGENT_WRITE_ROOTS','ANIME_AGENT_ALLOWED_COMMANDS','ANIME_AGENT_TTS_URL','ANIME_AGENT_TTS','ANIME_AGENT_VISION_BASE_URL','ANIME_AGENT_MCP_SERVERS','ANIME_AGENT_CONFIG_PATH','ANIME_AGENT_DATA_DIR'}}
secrets=[v for k,v in cfg.items() if any(x in k.upper() for x in ('KEY','TOKEN','PASSWORD','SECRET')) and len(v)>8]
def scrub(s):
    for v in secrets:s=s.replace(v,'<REDACTED>')
    s=re.sub(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', 'OWNER_TEST_MAILBOX', s)
    return s.replace(str(prod).replace('\\','/'),'<PRODUCTION>').replace(str(prod),'<PRODUCTION>').replace(str(prod.parent),'<WORK>')
db=db_connect(get(8765,'/health'))
mcp=[dict(r) for r in db.execute("SELECT id,event_type,payload,created_at FROM events WHERE event_type IN ('mcp.started','mcp.start.error') ORDER BY id DESC LIMIT 1")]
for r in mcp:r['payload']=json.loads(r['payload'])
integrity=[r[0] for r in db.execute('PRAGMA quick_check')]
tables=[dict(r) for r in db.execute("SELECT name,sql FROM sqlite_master WHERE type='table'")]
dependencies=[]
for f in prod.parent.iterdir():
    if f.is_dir() and (f/'.git').exists():
        try:dependencies.append({'directory':f.name,'head':git(f,'rev-parse','HEAD').decode().strip(),'branch':git(f,'branch','--show-current').decode().strip(),'status':git(f,'status','--porcelain').decode(),'remote':git(f,'remote','get-url','origin').decode().strip()})
        except subprocess.CalledProcessError:pass
tree=ast.parse((prod/'services/agent-core/agent_core/tools.py').read_text(encoding='utf-8'))
localtools=[]
for node in ast.walk(tree):
    if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='Tool':
        data={kw.arg:ast.literal_eval(kw.value) for kw in node.keywords if kw.arg in {'name','description','parameters','timeout'}}
        data['line']=node.lineno;localtools.append(data)
record={'kind':'read-only source/config/DB diagnostic; not frontend acceptance','config_allowlist':safe,'last_runtime_mcp_start':mcp,'db_quick_check':integrity,'schema':tables,'cross_repositories':dependencies,'local_tools':localtools,'runtime_only_tools':['read_tool_result','recall_memory'],'production_business_files_changed':False}
record=json.loads(scrub(json.dumps(record,ensure_ascii=False)))
save('inventory-start',record)
print(json.dumps(record,ensure_ascii=False,indent=2))
