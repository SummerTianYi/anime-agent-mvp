"""Index safety check, optionally including already-committed candidate changes.

Reports names/counts only, never secrets. --base-ref scans the index relative to
the agreed baseline, so earlier candidate commits are not missed at delivery.
"""
import argparse,json,subprocess
from pathlib import Path
from dotenv import dotenv_values
ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser();p.add_argument("--env-file",type=Path,required=True)
p.add_argument("--base-ref");a=p.parse_args()
values=dotenv_values(a.env_file)
secrets=[str(v) for k,v in values.items() if v and len(str(v))>=12 and any(x in k for x in ("KEY","TOKEN","SECRET","PASSWORD"))]
command=["git","diff","--cached","--name-only","--diff-filter=ACMRT"]
if a.base_ref:
    subprocess.run(["git","rev-parse","--verify",a.base_ref+"^{commit}"],cwd=ROOT,check=True,capture_output=True)
    command.append(a.base_ref)
names=subprocess.check_output(command,cwd=ROOT,text=True).splitlines()
errors=[]
for name in names:
    if name.startswith(("docs/assessments/harness-v0/","scripts/harness_v0/")):errors.append((name,"V0 changed"))
    if name.endswith((".sqlite3",".db",".env",".glb",".blend",".wav",".pth",".ckpt")):errors.append((name,"restricted artifact"))
    body=subprocess.check_output(["git","show",":"+name],cwd=ROOT)
    if len(body)>50*1024*1024:errors.append((name,"over 50MiB"))
    text=body.decode("utf-8",errors="replace")
    if any(s in text for s in secrets):errors.append((name,"credential match"))
print(json.dumps(dict(files=len(names),credential_values_compared=len(secrets),errors=errors),ensure_ascii=False))
raise SystemExit(bool(errors))
