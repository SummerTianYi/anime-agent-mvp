"""Codex: installed connector provenance + private pre-reauthorization backup."""
import argparse,hashlib,json,shutil
from pathlib import Path
from datetime import datetime,timezone
from probe import ROOT,save
p=argparse.ArgumentParser();p.add_argument('--production',type=Path,required=True);a=p.parse_args()
gmail=Path.home()/'AppData/Local/npm-cache/_npx/952459504b2da320/node_modules/@gongrzhe/server-gmail-autoauth-mcp'
package=json.loads((gmail/'package.json').read_text())
paths={'gmail dist/index.js':gmail/'dist/index.js','gmail launcher':a.production/'tools/gmail-mcp.cmd',
       'drive index.mjs':a.production/'tools/gdrive/index.mjs','drive oauth.mjs':a.production/'tools/gdrive/oauth.mjs',
       'GitHub MCP binary':a.production/'tools/github-mcp-server.exe'}
manifest={name:dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size) for name,path in paths.items()}
source=Path.home()/'.gmail-mcp/credentials.json'
backup=a.production/'runs/private-audit-preservation'/('gmail-before-auth-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
backup.mkdir(parents=True,exist_ok=False)
if source.is_file():
    shutil.copyfile(source,backup/'credentials.json')
save('connector-provenance',dict(utc=datetime.now(timezone.utc).isoformat(),gmail_version=package['version'],
    source=package['repository'],manifest=manifest,private_backup='<PRODUCTION>/runs/private-audit-preservation/'+backup.name,
    backed_up=source.is_file(),source_modified=False,
    gmail_error_contract={'line':1000,'behavior':'catch returns content:[{type:text,text:Error...}] without isError'},
    gmail_auth={'mode':'auth','callback_port':3000,'writes':'only credentials.json, not gdrive-credentials.json',
        'reload':'server loads credential once at startup; current child needs lifecycle restart'},
    drive_contract='only search tool; resources/read handler exists but Core has no exposed caller'))
print('Connector provenance saved; credentials backed up privately, not displayed; OAuth not started.')
