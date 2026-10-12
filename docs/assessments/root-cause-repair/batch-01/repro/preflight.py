"""Read-only deployment inventory and PRIVATE recovery material.

No Core import, migration, checkpoint, production write, or process control.
Reuses round-02 file identity and SQLite backup from a read transaction.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import time
from urllib.request import build_opener, ProxyHandler

sys.dont_write_bytecode = True


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(root, *arguments):
    return subprocess.check_output(['git','-C',str(root),*arguments])


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--production',type=Path,required=True)
    parser.add_argument('--tts',type=Path,required=True)
    parser.add_argument('--private-output',type=Path,required=True)
    parser.add_argument('--summary',type=Path,required=True)
    args=parser.parse_args()
    out=args.private_output.resolve()
    for repo in (args.production.resolve(),args.tts.resolve(),Path(__file__).resolve().parents[5]):
        if out==repo or repo in out.parents:
            raise ValueError('Private output must be outside every repository')
    out.mkdir(parents=True,exist_ok=False)
    source=Path(__file__).resolve().parents[5]
    sys.path.insert(0,str(source/'scripts'/'root_cause_audit'))
    from round02_identity import file_identity
    from dotenv import dotenv_values
    record={'utc':datetime.now(timezone.utc).isoformat(),'source_mutations':[],
            'desktop_observed':False,'deployment_process_association':'not established'}
    for name,root in (('main',args.production),('tts',args.tts)):
        section={'head':git(root,'rev-parse','HEAD').decode().strip(),
                 'status':git(root,'status','--porcelain').decode('utf-8')}
        (out/(name+'-uncommitted.patch')).write_bytes(git(root,'diff','HEAD','--binary'))
        paths=git(root,'ls-files','--cached','--others','--exclude-standard','-z').decode('utf-8').split('\0')
        hashes={}
        for rel in paths:
            path=root/rel
            if rel and path.is_file() and path.suffix in {'.py','.gd','.ps1','.cmd','.bat'} and not rel.startswith('out/'):
                hashes[rel]=digest(path)
                dest=out/name/rel
                dest.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(path,dest)
        section['source_hashes']=hashes
        record[name]=section
    env_file=args.production/'.env'
    config=dotenv_values(env_file) if env_file.exists() else {}
    if env_file.exists():
        shutil.copy2(env_file,out/'production-config.env')
        record['config_sha256']=digest(env_file)
    voice=args.tts/'configs'/'tianyi_voice_v2.json'
    if voice.exists():
        shutil.copy2(voice,out/'voice-config.json')
        record['voice_config_sha256']=digest(voice)
    record['settings']={key:os.environ.get(key,config.get(key)) for key in (
        'LLM_PROVIDER','DEEPSEEK_MODEL','GLM_MODEL','ANIME_AGENT_VOICE_INPUT_MODE',
        'ANIME_AGENT_QUIET_START','ANIME_AGENT_QUIET_END','ANIME_AGENT_IDLE_SECONDS')}
    opener=build_opener(ProxyHandler({}))
    for label,url in (('core','http://127.0.0.1:8765/health'),('tts_health','http://127.0.0.1:8770/health')):
        try:
            with opener.open(url,timeout=3) as response:
                record[label]=json.load(response)
        except Exception as exc:
            record[label]={'unavailable':True,'error_type':type(exc).__name__}
    configured=os.environ.get('ANIME_AGENT_DATA_DIR',config.get('ANIME_AGENT_DATA_DIR'))
    path=Path(configured) if configured else Path(os.environ['LOCALAPPDATA'])/'AnimeAgent'/'data'
    path=path/'anime-agent.sqlite3'
    if isinstance(record.get('core',{}).get('memory'),dict):
        path=Path(record['core']['memory']['path'])
    record['database']={'path_source':'live health' if 'memory' in record['core'] else 'configuration only'}
    db=record['database']
    try:
        db['normal_identity']=file_identity(path)
        physical=Path('\\\\localhost\\'+str(path)[0].lower()+'$\\'+str(path)[3:])
        db['unc_identity']=file_identity(physical)
        same=lambda a,b: all(a[k]==b[k] for k in ('volume_serial','file_index'))
        db['namespace_equal']=same(db['normal_identity'],db['unc_identity'])
        if not db['namespace_equal']:
            raise RuntimeError('Namespace mismatch; no database operations performed')
        with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True,timeout=3) as connection:
            connection.execute('PRAGMA query_only=ON')
            connection.execute('BEGIN')
            connection.execute('SELECT count(*) FROM sqlite_schema').fetchone()
            began=time.monotonic()
            def progress(*unused):
                if time.monotonic()-began>30:
                    raise TimeoutError('Backup deadline')
            snapshot=out/'transaction-snapshot.sqlite3'
            with sqlite3.connect(snapshot) as target:
                connection.backup(target,pages=64,progress=progress,sleep=.02)
            connection.rollback()
        with sqlite3.connect(snapshot.as_uri()+'?mode=ro',uri=True) as copied:
            db['quick_check']=[row[0] for row in copied.execute('PRAGMA quick_check')]
        db['identity_stable']=same(db['normal_identity'],file_identity(path))
        db['snapshot_sha256']=digest(snapshot)
        db['snapshot_method']='SQLite backup from explicit read transaction'
    except Exception as exc:
        db['error']={'type':type(exc).__name__,'message':str(exc)}
    (out/'PRIVATE-inventory.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    summary={key:record[key] for key in ('utc','source_mutations','desktop_observed','deployment_process_association')}
    summary['repositories']={name:{'head':record[name]['head'],
        'dirty_entries':len(record[name]['status'].splitlines()),'source_files_backed_up':len(record[name]['source_hashes'])}
        for name in ('main','tts')}
    summary['health']={name:record[name] if record[name].get('unavailable') else {'reachable':True}
                       for name in ('core','tts_health')}
    summary['database']={key:db.get(key) for key in ('path_source','namespace_equal','identity_stable','snapshot_method','snapshot_sha256')}
    summary['database']['quick_check_ok']=db.get('quick_check')==['ok']
    summary['database']['error_type']=db.get('error',{}).get('type')
    summary['database']['quick_check_messages']=len(db.get('quick_check',[]))
    args.summary.write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False))


if __name__=='__main__':
    main()
