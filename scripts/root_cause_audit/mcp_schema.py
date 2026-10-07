"""Metadata-only independent connector probe. NOT a Tianyi frontend task.

No tools/call, resources/read or external business operation. NPM offline mode;
only processes created by this probe (PID + creation time) may be terminated.
"""
import argparse,asyncio,json,os,sys
from pathlib import Path
from probe import ROOT,save
p=argparse.ArgumentParser();p.add_argument('--production',type=Path,required=True);a=p.parse_args()
sys.path.insert(0,str(a.production/'services/agent-core'))
sys.path.append(str(a.production.parent/'tianyi-tts/venv/Lib/site-packages'))
import psutil
from agent_core.mcp_host import McpServer,_split_command,_resolve_command
for line in (a.production/'.env').read_text(encoding='utf-8-sig').splitlines():
    k,sep,v=line.partition('=')
    if sep and k and not k.startswith('#'):os.environ[k.strip()]=v.strip().strip('"').strip("'")
os.environ['NPM_CONFIG_OFFLINE']='true'
async def main():
    rows=[]
    for entry in os.environ.get('ANIME_AGENT_MCP_SERVERS','').split(os.pathsep):
        name,sep,cmd=entry.partition('=')
        if not sep:continue
        server=McpServer(name=name,command=_resolve_command(_split_command(cmd)))
        children=[]
        try:
            await asyncio.wait_for(server.start(),25)
            rows.append({'server':name,'started':server.started,'tools':server.tools})
        except Exception as e:rows.append({'server':name,'started':False,'error_type':type(e).__name__})
        finally:
            if server.process:
                try:children=[(c.pid,c.create_time()) for c in psutil.Process(server.process.pid).children(recursive=True)]
                except psutil.Error:pass
                await server.stop()
                for pid,created in reversed(children):
                    try:
                        proc=psutil.Process(pid)
                        if proc.create_time()==created:proc.terminate()
                    except psutil.Error:pass
    record={'layer':'separate tools/list metadata probe; no tools/call; not current desktop authorization or functional acceptance','npm_offline':True,'servers':rows}
    save('mcp-schema',record)
    print(json.dumps([{'server':r['server'],'started':r['started'],'names':[t['name'] for t in r.get('tools',[])]} for r in rows],ensure_ascii=False,indent=2))
asyncio.run(main())
