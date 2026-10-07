"""Read-only check for Windows package file virtualization; no user text output."""
import json
import sqlite3
import ctypes
from urllib.parse import quote
from pathlib import Path
from probe import get

path=get(8765,'/health')['memory']['path']
candidates=[path, '\\\\?\\'+path, '\\\\localhost\\c$\\'+path[3:], str(Path.home()/'AppData/Local/Packages/OpenAI.Codex_2p2nqsd0c76g0/LocalCache/Local/AnimeAgent/data/anime-agent.sqlite3')]
buf=ctypes.create_unicode_buffer(1024)
ctypes.windll.kernel32.QueryDosDeviceW('C:',buf,1024)
candidates.append('\\\\?\\GLOBALROOT'+buf.value+'\\'+path[3:])
for value in candidates:
    try:
        p=Path(value)
        c=sqlite3.connect('file:'+quote(value,safe=':')+'?mode=ro',uri=True)
        c.execute('PRAGMA query_only=ON')
        rows=c.execute('SELECT id,request_id,conversation_id,created_at FROM messages ORDER BY id DESC LIMIT 1').fetchall()
        audit=c.execute("SELECT id,request_id,conversation_id,created_at FROM messages WHERE content LIKE '%根因审计%' AND created_at>='2026-10-07'").fetchall()
        print(json.dumps({'path':value,'size':p.stat().st_size,'latest_metadata':rows,'audit_metadata':audit},ensure_ascii=False))
    except Exception as e: print(json.dumps({'path':value,'error_type':type(e).__name__,'error':str(e)},ensure_ascii=False))
