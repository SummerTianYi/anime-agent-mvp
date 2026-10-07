"""Diagnostic only: compare main/WAL visibility without exposing row content."""
import hashlib,json,sqlite3,shutil,tempfile
from pathlib import Path
from probe import get
reported=get(8765,'/health')['memory']['path']
native=Path('\\\\localhost\\'+reported[0].lower()+'$\\'+reported[3:])
record={}
for base in (Path(reported),native):
    record[str(base)]={}
    for ext in ('','-wal','-shm'):
        p=Path(str(base)+ext)
        record[str(base)][ext or 'main']={'exists':p.exists(),'bytes':p.stat().st_size if p.exists() else None}
with tempfile.TemporaryDirectory(prefix='tianyi-readonly-audit-') as temp:
    dest=Path(temp)/'view.sqlite3'
    before={}
    for ext in ('','-wal'):
        p=Path(str(native)+ext)
        if p.exists():
            before[ext]=hashlib.sha256(p.read_bytes()).hexdigest()
            shutil.copyfile(p,Path(str(dest)+ext))
    after={ext:hashlib.sha256(Path(str(native)+ext).read_bytes()).hexdigest() for ext in before}
    assert before==after,'Source changed during copy; snapshot unusable'
    db=sqlite3.connect(dest.as_uri()+'?mode=ro',uri=True)
    record['copied_stable_main_wal_audit_metadata']=db.execute("SELECT id,request_id,conversation_id,created_at FROM messages WHERE role='user' AND (content LIKE '[RA-%' OR content LIKE '天依你好，这是根因审计%')").fetchall()
    db.close()
print(json.dumps(record,ensure_ascii=False,indent=2))
