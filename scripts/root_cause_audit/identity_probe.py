"""Codex diagnostic: process namespace identity only; no Core or DB writes."""
import argparse, ctypes, hashlib, json, os
from pathlib import Path

p=argparse.ArgumentParser(); p.add_argument('--output', type=Path, required=True); a=p.parse_args()
length=ctypes.c_uint32(0)
package_result=ctypes.windll.kernel32.GetCurrentPackageFullName(ctypes.byref(length), None)
normal=Path(os.environ['LOCALAPPDATA'])/'AnimeAgent/data/anime-agent.sqlite3'
physical=Path('\\\\localhost\\'+str(normal)[0].lower()+'$\\'+str(normal)[3:])
def digest(path):
    return {ext: hashlib.sha256(Path(str(path)+ext).read_bytes()).hexdigest()
            for ext in ('','-wal') if Path(str(path)+ext).is_file()}
out={'pid':os.getpid(),'package_query_status':package_result,'unpackaged':package_result==15700,
     'normal_path':str(normal),'physical_path':str(physical),
     'normal_size':normal.stat().st_size,'physical_size':physical.stat().st_size,
     'normal':digest(normal),'physical':digest(physical),'no_database_write':True}
out['same_namespace_snapshot']=out['normal']==out['physical']
a.output.parent.mkdir(parents=True, exist_ok=True)
with a.output.open('x',encoding='utf-8') as f: json.dump(out,f,indent=2)
