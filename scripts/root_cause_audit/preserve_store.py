"""Make a private SQLite backup before synthetic desktop writes; never repair source."""
import argparse
import sqlite3
from datetime import datetime,timezone
from pathlib import Path
from probe import db_connect,get,save,sha
p=argparse.ArgumentParser();p.add_argument('--private-root',type=Path,required=True);a=p.parse_args()
target=a.private_root/('root-cause-audit-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
target.mkdir(parents=True,exist_ok=False)
source=db_connect(get(8765,'/health'))
dest=target/'pre-audit.sqlite3'
connection=sqlite3.connect(dest)
try:
    source.backup(connection,pages=128,sleep=.05)
    connection.close()
    save('preservation',{'utc':datetime.now(timezone.utc).isoformat(),'private_backup':'<PRIVATE_AUDIT_BACKUP>/'+target.name+'/pre-audit.sqlite3','sha256':sha(dest.read_bytes()),'bytes':dest.stat().st_size,'kind':'SQLite consistent backup; original corruption preserved, not repaired; no restore performed'})
    print('PRIVATE_BACKUP='+str(dest))
finally:
    connection.close();source.close()
