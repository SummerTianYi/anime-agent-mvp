"""Bounded staged-publication check. Prints paths/reasons, never secret values."""
import argparse
import json
from pathlib import Path
import re
import subprocess


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('repo',type=Path)
    args=parser.parse_args()
    def git(*parts):
        return subprocess.check_output(['git','-C',str(args.repo),*parts])
    paths=git('diff','--cached','--name-only','--diff-filter=ACM','-z').decode().split('\0')
    secrets=[rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',rb'gh[pousr]_[A-Za-z0-9]{30,}',
             rb'github_pat_[A-Za-z0-9_]{30,}',rb'AIza[0-9A-Za-z_-]{30,}',rb'sk-[A-Za-z0-9_-]{28,}']
    failures=[]; sizes={}
    for path in filter(None,paths):
        blob=git('show',':'+path)
        sizes[path]=len(blob)
        if len(blob)>50*1024*1024:
            failures.append([path,'over 50 MiB'])
        if Path(path).suffix.lower() in {'.sqlite3','.db','.wav','.mp3','.glb','.ckpt','.pth'} or Path(path).name=='.env':
            failures.append([path,'private/runtime file type'])
        if any(re.search(pattern,blob) for pattern in secrets):
            failures.append([path,'possible credential; inspect privately'])
    print(json.dumps({'files':len(sizes),'max_bytes':max(sizes.values(),default=0),'failures':failures}))
    return bool(failures)


if __name__=='__main__':
    raise SystemExit(main())
